"""
emotion/classifier.py

CONCEPT (Parts 10, 11, 35 - separating training from inference):
---------------------------------------------------------------------
This module NO LONGER trains a model at import time. Training now lives
entirely in evaluate_model.py (run once, offline, produces a saved
emotion/model.joblib). This file just LOADS that saved model and serves
predictions - exactly the separation Part 35 asks for:

    data preprocessing -> feature extraction -> model training -> model
    evaluation -> model saving   (all in evaluate_model.py)
                                        v
                              model loading -> prediction  (this file)

If emotion/model.joblib does not exist yet, this raises a clear error
telling you to run evaluate_model.py first, rather than silently retraining
on unevaluated data inside a web request (Part 33: "Do not let the
chatbot's production model silently evaluate itself on training data").

RASA NOTE (Part 3): if your course requires Rasa specifically, replace the
body of predict() with a call to a trained Rasa NLU model's /model/parse
endpoint, keeping the same (emotion, confidence, all_scores) return shape.
Nothing else in the project needs to change - see README.md.
"""

import logging
import joblib
import config

logger = logging.getLogger("mh_chatbot.emotion")


class ModelNotTrainedError(RuntimeError):
    pass


class EmotionClassifier:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or config.MODEL_PATH
        self.model = self._load()

    def _load(self):
        try:
            return joblib.load(self.model_path)
        except FileNotFoundError:
            raise ModelNotTrainedError(
                f"No trained model found at '{self.model_path}'. "
                "Run `python evaluate_model.py` first to train, evaluate, "
                "and save the emotion classifier."
            )

    def predict(self, text: str):
        """
        Returns:
            emotion (str or None): highest-probability emotion label
            confidence (float): probability of that top label (0-1)
            all_scores (dict): emotion -> probability, for every class
        """
        if not text or not text.strip():
            uniform = 1.0 / len(self.model.classes_)
            return None, 0.0, {c: uniform for c in self.model.classes_}

        proba = self.model.predict_proba([text])[0]
        classes = self.model.classes_
        all_scores = {cls: float(p) for cls, p in zip(classes, proba)}

        top_idx = proba.argmax()
        top_emotion = classes[top_idx]
        top_confidence = float(proba[top_idx])

        return top_emotion, top_confidence, all_scores
