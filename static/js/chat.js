// static/js/chat.js
//
// CONCEPT (Part 26 - XSS protection):
// Every piece of text that could contain user- or resource-supplied
// content is inserted via textContent / createElement, never innerHTML.
// This means even if a resource title or a user message contained HTML
// special characters, it would render as plain text, not be parsed as
// markup.
//
// CONCEPT (Part 16 - User Correction):
// After a MODEL-based response (correctable === true), a small
// "Did I get that right?" prompt appears. Clicking "No, let me choose"
// opens the same style of guided menu so the user can pick the emotion
// they actually meant; that correction is sent to /api/correct.

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const guidedAreaEl = document.getElementById("guided-area");
const optionsEl = document.getElementById("guided-options");
const correctionAreaEl = document.getElementById("correction-area");
const correctionOptionsEl = document.getElementById("correction-options");
const correctionYesBtn = document.getElementById("correction-yes");
const correctionNoBtn = document.getElementById("correction-no");
const videoLanguageEl = document.getElementById("video-language");
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

function selectedVideoLanguage() {
  return videoLanguageEl?.value === "hi" ? "hi" : "en";
}

// Map from display label to the emotion key the backend expects.
const LABEL_TO_EMOTION = {
    "Calm / Okay": "neutral",
    "Worried": "fear",
    "Sad": "sadness",
    "Angry": "anger",
    "Stressed": "stress",
    "Not sure": ""
};

let lastPredictedEmotion = null; // for correction requests

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.textContent = text; // safe: never innerHTML
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addResources(resources) {
  resources.forEach(r => {
    const card = document.createElement("div");
    card.className = "resource-card";

    const title = document.createElement("strong");
    title.textContent = r.title || "";
    card.appendChild(title);
    card.appendChild(document.createElement("br"));

    const type = document.createElement("span");
    type.className = "resource-type";
    type.textContent = r.resource_type === "video" ? "Video" : (r.resource_type || "Resource");
    card.appendChild(type);
    card.appendChild(document.createElement("br"));

    if (r.resource_type === "video" && r.generated && r.url) {
      const video = document.createElement("video");
      video.controls = true;
      video.preload = "metadata";
      video.playsInline = true;
      video.src = r.url;
      video.className = "generated-video";
      card.appendChild(video);
      card.appendChild(document.createElement("br"));
    } else {
      const link = document.createElement("a");
      link.href = r.url || "#";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = r.source ? `Open ${r.source} video/resource` : "Open resource";
      card.appendChild(link);
      card.appendChild(document.createElement("br"));
    }

    const desc = document.createElement("span");
    desc.textContent = r.description || "";
    card.appendChild(desc);

    if (r.match_score !== undefined) {
      const match = document.createElement("small");
      match.textContent = " Selected because it matches the conversation context and problem.";
      card.appendChild(document.createElement("br"));
      card.appendChild(match);
    }

    messagesEl.appendChild(card);
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function clearGuidedOptions() {
  optionsEl.textContent = "";
  guidedAreaEl.style.display = "none";
}

function renderGuidedOptions(labels) {
  clearGuidedOptions();
  if (!labels || labels.length === 0) return;

  guidedAreaEl.style.display = "block";
  labels.forEach(label => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.onclick = () => sendGuidedChoice(label, LABEL_TO_EMOTION[label]);
    optionsEl.appendChild(btn);
  });
}

function hideCorrectionPrompt() {
  correctionAreaEl.style.display = "none";
  correctionOptionsEl.style.display = "none";
  correctionOptionsEl.textContent = "";
}

function showCorrectionPrompt(predictedEmotion) {
  lastPredictedEmotion = predictedEmotion;
  correctionAreaEl.style.display = "flex";
}

async function sendToServer(url, payload) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({ ...payload, video_language: selectedVideoLanguage() })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok && !data.error) {
      data.error = "The request could not be completed. Please refresh the page and try again.";
    }
    return data;
  } catch (error) {
    return { error: "Could not reach the chatbot. Check that the server is running and try again." };
  }
}

async function sendGuidedChoice(label, emotionValue) {
  addMessage(label, "user");
  clearGuidedOptions();
  hideCorrectionPrompt();
  const data = await sendToServer("/api/chat", { message: "", guided_emotion: emotionValue });
  handleBotResponse(data);
}

function handleBotResponse(data) {
  if (data.error) {
    addMessage("Sorry, something went wrong. Please try again.", "bot");
    return;
  }
  addMessage(data.reply || "I couldn't prepare a response. Please try again.", data.type === "safety" ? "safety" : "bot");
  renderGuidedOptions(data.guided_options);

  if (data.resources && data.resources.length > 0) {
    addResources(data.resources);
  }

  hideCorrectionPrompt();
  if (data.correctable) {
    showCorrectionPrompt(data.emotion);
  }
}

correctionYesBtn.addEventListener("click", () => {
  hideCorrectionPrompt();
});

correctionNoBtn.addEventListener("click", () => {
  correctionOptionsEl.style.display = "flex";
  correctionOptionsEl.textContent = "";
  Object.entries(LABEL_TO_EMOTION).forEach(([label, emotion]) => {
    if (label === "Not sure") return; // correction implies the user does know
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.onclick = () => sendCorrection(label, emotion);
    correctionOptionsEl.appendChild(btn);
  });
});

async function sendCorrection(label, emotion) {
  addMessage(`Actually, ${label}`, "user");
  hideCorrectionPrompt();
  const data = await sendToServer("/api/correct", {
    predicted_emotion: lastPredictedEmotion,
    corrected_emotion: emotion
  });
  handleBotResponse(data);
}

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  addMessage(text, "user");
  inputEl.value = "";
  hideCorrectionPrompt();
  const data = await sendToServer("/api/chat", { message: text });
  handleBotResponse(data);
});
