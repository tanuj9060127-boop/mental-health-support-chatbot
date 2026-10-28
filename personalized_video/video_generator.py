"""Render an MP4 slideshow with synchronized English or Hindi narration.

The slide generation is local. Speech synthesis uses the gTTS online service;
if speech synthesis fails, this module raises an error rather than silently
creating another video without audio.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

import config
from personalized_video.tts import synthesize_speech

FPS = 2
WIDTH, HEIGHT = 960, 544


def _wrap(text: str, width: int = 48) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _load_fonts(language: str):
    from PIL import ImageFont

    if language == "hi":
        candidates = [
            config.HINDI_FONT_PATH,
            "C:/Windows/Fonts/Nirmala.ttf",
            "C:/Windows/Fonts/NirmalaB.ttf",
            "C:/Windows/Fonts/mangal.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for candidate in candidates:
        if not candidate or not os.path.isfile(candidate):
            continue
        try:
            title_font = ImageFont.truetype(candidate, 42)
            body_font = ImageFont.truetype(candidate, 29)
            return title_font, body_font
        except OSError:
            continue

    if language == "hi":
        raise RuntimeError(
            "A Devanagari font is required for Hindi video captions. Install a font such as Nirmala UI or Noto Sans Devanagari, or set HINDI_FONT_PATH."
        )
    return ImageFont.load_default(), ImageFont.load_default()


def _build_slide(title, section, index, count, fonts, language):
    import numpy as np
    from PIL import Image, ImageDraw

    title_font, body_font = fonts
    image = Image.new("RGB", (WIDTH, HEIGHT), (245, 247, 250))
    draw = ImageDraw.Draw(image)

    # Keep title within the frame if the translated title is long.
    title_lines = _wrap(title, 34 if language == "hi" else 38)[:2]
    title_y = 36
    for title_line in title_lines:
        draw.text((54, title_y), title_line, font=title_font, fill=(30, 35, 45))
        title_y += 54

    y = max(145, title_y + 28)
    body_lines = _wrap(section, 43 if language == "hi" else 52)
    for line in body_lines[:6]:
        draw.text((62, y), line, font=body_font, fill=(50, 55, 65))
        y += 46

    footer = f"शैक्षिक सहायता • {index}/{count}" if language == "hi" else f"Educational support • {index}/{count}"
    draw.text((54, HEIGHT - 48), footer, font=body_font, fill=(90, 95, 105))
    return np.asarray(image)


def render_video(script_data: dict, output_dir: str | os.PathLike, language: str = "en") -> str:
    """Create a narrated MP4 and return its absolute file path."""
    if language not in {"en", "hi"}:
        raise ValueError("Video language must be 'en' or 'hi'.")

    title = str(script_data.get("title") or "A short wellbeing guide").strip()
    sections = [str(item).strip() for item in (script_data.get("sections") or []) if str(item).strip()]
    if not sections:
        raise ValueError("A video script must contain at least one narration section.")

    try:
        from PIL import ImageFont  # noqa: F401 - dependency check
        import imageio.v2 as imageio
        import imageio_ffmpeg
        from mutagen.mp3 import MP3
        import numpy as np  # noqa: F401 - used by _build_slide
    except ImportError as exc:
        raise RuntimeError(
            "Video generation requires Pillow, imageio, imageio-ffmpeg, and mutagen. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_").lower()[:48] or "wellbeing_guide"
    final_path = output_root / f"{safe_name}_{language}_{uuid.uuid4().hex[:10]}.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    fonts = _load_fonts(language)

    with tempfile.TemporaryDirectory(prefix="video_build_") as temporary_dir:
        temp = Path(temporary_dir)
        audio_path = temp / "narration.mp3"
        silent_path = temp / "slides.mp4"
        narration = " ".join(sections)
        synthesize_speech(narration, audio_path, language)

        try:
            duration = float(MP3(str(audio_path)).info.length)
        except Exception as exc:
            raise RuntimeError("The generated narration audio could not be read.") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise RuntimeError("The generated narration has an invalid duration.")
        if duration > config.VIDEO_MAX_SECONDS:
            raise RuntimeError(
                f"Narration is longer than the configured limit of {config.VIDEO_MAX_SECONDS} seconds."
            )

        # Allocate slide frames in proportion to narration length, plus a small
        # tail so `-shortest` ends with the audio rather than cutting it off.
        target_frames = max(len(sections), math.ceil(duration * FPS) + FPS)
        weights = [max(1, len(text.split())) for text in sections]
        weight_total = sum(weights)
        frame_counts = [max(1, int(target_frames * weight / weight_total)) for weight in weights]
        while sum(frame_counts) < target_frames:
            idx = max(range(len(weights)), key=lambda i: weights[i])
            frame_counts[idx] += 1
        while sum(frame_counts) > target_frames and any(count > 1 for count in frame_counts):
            idx = max((i for i, count in enumerate(frame_counts) if count > 1), key=lambda i: frame_counts[i])
            frame_counts[idx] -= 1

        try:
            with imageio.get_writer(
                str(silent_path),
                fps=FPS,
                codec="libx264",
                macro_block_size=16,
                pixelformat="yuv420p",
            ) as writer:
                total = len(sections)
                for idx, section in enumerate(sections, start=1):
                    frame = _build_slide(title, section, idx, total, fonts, language)
                    for _ in range(frame_counts[idx - 1]):
                        writer.append_data(frame)
        except Exception as exc:
            raise RuntimeError("The slideshow portion of the video could not be rendered.") from exc

        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(final_path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
            if completed.returncode != 0:
                final_path.unlink(missing_ok=True)
                raise RuntimeError("FFmpeg could not combine the slides and narration.")
            # Verify that the final MP4 has a decodable audio stream.
            audio_check = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(final_path), "-map", "0:a:0", "-f", "null", "-"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            video_check = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(final_path), "-f", "null", "-"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if audio_check.returncode != 0 or video_check.returncode != 0:
                final_path.unlink(missing_ok=True)
                raise RuntimeError("The generated MP4 did not pass audio/video decoding checks.")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Video rendering took too long and was stopped.") from exc
        finally:
            if final_path.exists() and final_path.stat().st_size < 1024:
                final_path.unlink(missing_ok=True)

    if not final_path.is_file() or final_path.stat().st_size < 1024:
        raise RuntimeError("The generated MP4 is empty or incomplete.")
    return str(final_path)
