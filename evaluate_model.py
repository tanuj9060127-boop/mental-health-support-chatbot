"""
evaluate_model.py

CONCEPT (Parts 9, 10, 33, 34, 35 - Proper Dataset Splitting & ML Evaluation):
---------------------------------------------------------------------------
This is the ONE script that owns the full model lifecycle, kept separate
from the Flask request-handling code (Part 35: "do not mix all training
logic directly into the Flask request handler"):

    load dataset
         v
    stratified train/validation/test split   (Part 9)
         v
    train on TRAIN only
         v
    evaluate on VALIDATION (used to sanity-check / tune the confidence
    threshold - Part 8: "selected using validation data")
         v
    evaluate on TEST (held out, never seen during training or tuning -
    this is the honest, unbiased accuracy/precision/recall/F1 number)
         v
    print + save a real evaluation report (Part 10 - numbers are computed,
    never invented)
         v
    fit a final "deployment" model on ALL data and save it to disk with
    joblib (Part 34 - reproducible training, fixed random seed, saved
    model) so the Flask app's classifier.py never retrains at runtime.

WHY RETRAIN ON ALL DATA FOR THE DEPLOYED MODEL:
    Evaluating on a held-out test set gives you an honest accuracy number.
    But once that number is recorded, throwing away 30% of your already-
    small dataset for the model that actually talks to users is wasteful.
    Standard practice: evaluate on a split, then fit the final deployed
    model on all available data. The reported metrics above are the ones
    that matter for your project report - they were NOT computed on data
    the deployed model was trained on.

RUN THIS: python evaluate_model.py
    - Prints dataset size, per-class counts, and split sizes
    - Prints validation-set metrics
    - Prints test-set classification report + confusion matrix
    - Saves emotion/evaluation_report.txt
    - Saves emotion/model.joblib (used by emotion/classifier.py at runtime)
"""

import csv
import json
import random
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

import config
from pathlib import Path

RANDOM_SEED = 42  # fixed seed -> reproducible split and training (Part 34)


def load_dataset(path):
    texts, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row["text"])
            labels.append(row["emotion"])
    return texts, labels


def build_pipeline():
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)),
    ])


def format_confusion_matrix(cm, labels):
    lines = []
    header = "".join(f"{l[:8]:>10}" for l in labels)
    lines.append(" " * 12 + header)
    for i, label in enumerate(labels):
        row = "".join(f"{cm[i][j]:>10}" for j in range(len(labels)))
        lines.append(f"{label[:10]:<12}{row}")
    return "\n".join(lines)


def main():
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    texts, labels = load_dataset(config.DATASET_PATH)
    class_counts = Counter(labels)
    n_total = len(texts)

    report_lines = []
    report_lines.append("Adaptive Mental Health Chatbot - Emotion Classifier Evaluation")
    report_lines.append("=" * 65)
    try:
        dataset_label = Path(config.DATASET_PATH).resolve().relative_to(Path(__file__).resolve().parent).as_posix()
    except ValueError:
        dataset_label = Path(config.DATASET_PATH).name
    report_lines.append(f"Dataset file: {dataset_label}")
    report_lines.append(f"Dataset size: {n_total}")
    report_lines.append("")
    report_lines.append("Examples per class:")
    for cls, count in sorted(class_counts.items()):
        report_lines.append(f"  {cls:<12} {count}")
    report_lines.append("")

    # --- Stratified 70/15/15 train/val/test split (Part 9) ---
    X_train, X_temp, y_train, y_temp = train_test_split(
        texts, labels, test_size=0.30, random_state=RANDOM_SEED, stratify=labels
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=RANDOM_SEED, stratify=y_temp
    )

    report_lines.append(f"Train: {len(X_train)}   Validation: {len(X_val)}   Test: {len(X_test)}")
    report_lines.append("")

    # --- Train on TRAIN only ---
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    # --- Validation metrics (Part 8: used to sanity-check the confidence
    #     threshold, NOT the final reported accuracy) ---
    val_preds = pipeline.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    report_lines.append("-" * 65)
    report_lines.append("VALIDATION SET (used only for threshold/tuning decisions)")
    report_lines.append("-" * 65)
    report_lines.append(f"Validation accuracy: {val_acc:.3f}")
    report_lines.append("")

    # --- Final, honest TEST set evaluation (never used for tuning) ---
    test_preds = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    labels_sorted = sorted(class_counts.keys())

    report_lines.append("-" * 65)
    report_lines.append("TEST SET (held out, final unbiased evaluation)")
    report_lines.append("-" * 65)
    report_lines.append(f"Test accuracy: {test_acc:.3f}")
    report_lines.append("")
    report_lines.append("Classification report (precision / recall / F1 per class):")
    report_lines.append(classification_report(y_test, test_preds, labels=labels_sorted, zero_division=0))

    cm = confusion_matrix(y_test, test_preds, labels=labels_sorted)
    report_lines.append("Confusion matrix (rows = actual, columns = predicted):")
    report_lines.append(format_confusion_matrix(cm, labels_sorted))
    report_lines.append("")

    report_lines.append("-" * 65)
    report_lines.append("NOTES / LIMITATIONS (see also README.md and Part 31)")
    report_lines.append("-" * 65)
    report_lines.append(
        "- This dataset is small (a few dozen examples per class). These\n"
        "  numbers describe how this specific model performs on this\n"
        "  specific held-out split - they are NOT a general claim about\n"
        "  real-world accuracy on unseen users' phrasing.\n"
        "- The model is NOT clinically validated and does not diagnose\n"
        "  any mental-health condition. It classifies expressed emotional\n"
        "  language only.\n"
        "- CONFIDENCE_THRESHOLD (config.py) is an application-level\n"
        "  decision threshold, not a clinical confidence measure."
    )

    report_text = "\n".join(report_lines)
    print(report_text)

    report_path = config.DATASET_PATH.replace("dataset.csv", "evaluation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nSaved evaluation report to: {report_path}")

    # --- Fit final deployment model on ALL data and save it (Part 34/35) ---
    deployment_pipeline = build_pipeline()
    deployment_pipeline.fit(texts, labels)
    joblib.dump(deployment_pipeline, config.MODEL_PATH)
    print(f"Saved deployment model to: {config.MODEL_PATH}")
    print(
        "\nNOTE: the deployment model above is trained on ALL available data "
        "(train+val+test combined), which is standard practice once "
        "evaluation is complete. The accuracy/F1 numbers reported above "
        "came from the held-out test set BEFORE this final refit."
    )


if __name__ == "__main__":
    main()
