import os
import re
import pickle
import logging
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing.sequence import pad_sequences
except ModuleNotFoundError:
    from keras.models import load_model
    from keras.utils import pad_sequences

from transformers import pipeline


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")

HF_TOKEN = os.getenv("HF_TOKEN")
TRANSFORMER_MODEL_ID = os.getenv("TRANSFORMER_MODEL_ID", "hamzab/roberta-fake-news-classification")

LSTM_MODEL_PATH = Path(os.getenv("LSTM_MODEL_PATH", PROJECT_ROOT / "Trained_Model.keras"))
LSTM_TOKENIZER_PATH = Path(os.getenv("LSTM_TOKENIZER_PATH", PROJECT_ROOT / "tokenizer.pkl"))
LSTM_MAX_LEN = int(os.getenv("LSTM_MAX_LEN", "300"))
LSTM_THRESHOLD = float(os.getenv("LSTM_THRESHOLD", "0.5"))

HYBRID_WEIGHT_TRANSFORMER = float(os.getenv("HYBRID_WEIGHT_TRANSFORMER", "0.6"))
HYBRID_WEIGHT_LSTM = float(os.getenv("HYBRID_WEIGHT_LSTM", "0.4"))
HYBRID_REAL_THRESHOLD = float(os.getenv("HYBRID_REAL_THRESHOLD", "0.62"))
HYBRID_FAKE_THRESHOLD = float(os.getenv("HYBRID_FAKE_THRESHOLD", "0.38"))

transformer_classifier = None
lstm_model = None
lstm_tokenizer = None


class DetectRequest(BaseModel):
    text: str


def _normalize_label(raw_label: str) -> str:
    label = str(raw_label).strip().upper()
    if "FAKE" in label:
        return "FAKE"
    if "REAL" in label or "TRUE" in label:
        return "REAL"
    if label in {"LABEL_0", "0"}:
        return "FAKE"
    if label in {"LABEL_1", "1"}:
        return "REAL"
    return "UNKNOWN"


def _load_transformer() -> None:
    global transformer_classifier
    logger.info("Loading transformer model: %s", TRANSFORMER_MODEL_ID)
    transformer_classifier = pipeline(
        "text-classification",
        model=TRANSFORMER_MODEL_ID,
        token=HF_TOKEN if HF_TOKEN else None,
        framework="pt",
        device=-1,
    )


def _load_lstm() -> None:
    global lstm_model, lstm_tokenizer

    if not LSTM_MODEL_PATH.exists():
        raise FileNotFoundError(f"LSTM model not found at {LSTM_MODEL_PATH}")
    if not LSTM_TOKENIZER_PATH.exists():
        raise FileNotFoundError(f"LSTM tokenizer not found at {LSTM_TOKENIZER_PATH}")

    logger.info("Loading LSTM model from %s", LSTM_MODEL_PATH)
    lstm_model = load_model(str(LSTM_MODEL_PATH))

    logger.info("Loading tokenizer from %s", LSTM_TOKENIZER_PATH)
    with open(LSTM_TOKENIZER_PATH, "rb") as file_obj:
        lstm_tokenizer = pickle.load(file_obj)


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [item.strip() for item in parts if item.strip()]


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current and current_len + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def _predict_transformer_prob_real(text: str) -> float:
    if transformer_classifier is None:
        raise RuntimeError("Transformer classifier is not loaded")

    results = transformer_classifier(text, truncation=True, max_length=512)
    if not isinstance(results, list) or not results:
        raise ValueError("Unexpected transformer output format")

    top = results[0]
    label = _normalize_label(top.get("label", "UNKNOWN"))
    score = float(top.get("score", 0.0))

    if label == "REAL":
        return float(np.clip(score, 0.0, 1.0))
    if label == "FAKE":
        return float(np.clip(1.0 - score, 0.0, 1.0))
    return 0.5


def _predict_lstm_prob_real(text: str) -> float:
    if lstm_model is None or lstm_tokenizer is None:
        raise RuntimeError("LSTM model/tokenizer not loaded")

    sequence = lstm_tokenizer.texts_to_sequences([text])
    padded = pad_sequences(
        sequence,
        maxlen=LSTM_MAX_LEN,
        padding="post",
        truncating="post",
    )

    prob_real = float(lstm_model.predict(padded, verbose=0)[0][0])
    return float(np.clip(prob_real, 0.0, 1.0))


def _hybrid_prob_real(text: str) -> dict:
    available_scores = {}

    try:
        available_scores["transformer"] = _predict_transformer_prob_real(text)
    except Exception as exc:
        logger.warning("Transformer scoring failed: %s", exc)

    try:
        available_scores["lstm"] = _predict_lstm_prob_real(text)
    except Exception as exc:
        logger.warning("LSTM scoring failed: %s", exc)

    if not available_scores:
        raise RuntimeError("No model was available for scoring")

    if "transformer" in available_scores and "lstm" in available_scores:
        total_weight = HYBRID_WEIGHT_TRANSFORMER + HYBRID_WEIGHT_LSTM
        if total_weight <= 0:
            total_weight = 1.0
        prob_real = (
            available_scores["transformer"] * HYBRID_WEIGHT_TRANSFORMER
            + available_scores["lstm"] * HYBRID_WEIGHT_LSTM
        ) / total_weight
        source = "hybrid"
    elif "transformer" in available_scores:
        prob_real = available_scores["transformer"]
        source = "transformer-only"
    else:
        prob_real = available_scores["lstm"]
        source = "lstm-only"

    prob_real = float(np.clip(prob_real, 0.0, 1.0))
    return {
        "prob_real": prob_real,
        "prob_fake": 1.0 - prob_real,
        "scores": available_scores,
        "source": source,
    }


def _consensus(prob_real: float) -> tuple[str, str, float]:
    prob_fake = 1.0 - prob_real
    prediction = "REAL" if prob_real >= 0.5 else "FAKE"
    confidence = max(prob_real, prob_fake)

    if prob_real >= HYBRID_REAL_THRESHOLD:
        return "Credible", "REAL", confidence
    if prob_real <= HYBRID_FAKE_THRESHOLD:
        return "Not credible", "FAKE", confidence
    return "Unverifiable / insufficient evidence", "UNCERTAIN", confidence


def _build_claims(text: str, limit: int = 5) -> list[str]:
    sentences = _split_sentences(text)
    claims = [s[:300] for s in sentences if len(s) > 20]
    if not claims:
        claims = ["Verify: " + text[:150]]
    return claims[:limit]


def _build_evidence_prompts(claims: list[str]) -> list[dict]:
    prompts = []
    for claim in claims:
        prompts.append(
            {
                "claim": claim,
                "questions": [
                    "What primary source supports or refutes this claim?",
                    "Is there independent coverage from credible outlets?",
                    "Are dates, locations, and actors consistent across sources?",
                ],
            }
        )
    return prompts


def _build_signals(text: str, confidence: float) -> list[dict]:
    signals = []

    if confidence > 0.85:
        signals.append({"type": "score", "text": "High confidence prediction", "impact": 0.25})
    elif confidence > 0.65:
        signals.append({"type": "score", "text": "Moderate confidence", "impact": 0.15})
    else:
        signals.append({"type": "score", "text": "Low confidence - verify independently", "impact": 0.10})

    text_lower = text.lower()
    sensational_words = ["shocking", "unbelievable", "amazing", "secret", "exposed", "revealed"]
    sensational_count = sum(1 for word in sensational_words if word in text_lower)
    if sensational_count >= 2:
        signals.append({"type": "language", "text": "Contains sensational language", "impact": 0.12})

    words = text.split()
    if words:
        caps_ratio = sum(1 for word in words if word.isupper() and len(word) > 2) / len(words)
        if caps_ratio > 0.12:
            signals.append({"type": "language", "text": "Excessive capitalization detected", "impact": 0.10})

    return signals


def _build_rationale(label: str, confidence: float, source: str) -> list[str]:
    rationale = [f"Decision source: {source}."]

    if label == "FAKE":
        if confidence >= 0.8:
            rationale.append("Both model evidence and confidence suggest misinformation risk.")
        else:
            rationale.append("Some signs of unreliability were detected, but confidence is moderate.")
    elif label == "REAL":
        if confidence >= 0.8:
            rationale.append("Evidence from the model stack points to credible content.")
        else:
            rationale.append("Content appears more credible than not, but additional verification is advised.")
    else:
        rationale.append("Model outputs are too close, so the result is marked uncertain.")

    rationale.append("Always verify major claims with independent sources.")
    return rationale


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "null",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    transformer_error = None
    lstm_error = None

    try:
        _load_transformer()
        logger.info("Transformer loaded")
    except Exception as exc:
        transformer_error = str(exc)
        logger.exception("Transformer load failed")

    try:
        _load_lstm()
        logger.info("LSTM loaded")
    except Exception as exc:
        lstm_error = str(exc)
        logger.exception("LSTM load failed")

    if transformer_error and lstm_error:
        logger.error("Both models failed to load. API will run but inference endpoints will error.")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok" if (transformer_classifier is not None or lstm_model is not None) else "degraded",
        "mode": "hybrid",
        "transformer_model": TRANSFORMER_MODEL_ID,
        "lstm_model_path": str(LSTM_MODEL_PATH),
        "lstm_tokenizer_path": str(LSTM_TOKENIZER_PATH),
        "models_loaded": {
            "transformer": transformer_classifier is not None,
            "lstm": lstm_model is not None and lstm_tokenizer is not None,
        },
        "weights": {
            "transformer": HYBRID_WEIGHT_TRANSFORMER,
            "lstm": HYBRID_WEIGHT_LSTM,
        },
    }


@app.post("/detect")
def detect(payload: DetectRequest) -> dict:
    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

    try:
        hybrid = _hybrid_prob_real(text)
        prob_real = hybrid["prob_real"]
        consensus, final_label, confidence = _consensus(prob_real)

        return {
            "model_used": "hybrid-transformer-lstm",
            "lstm": {
                "label": final_label,
                "confidence": confidence,
                "signals": _build_signals(text, confidence),
            },
            "llm": {
                "ran": True,
                "label": final_label if final_label in {"REAL", "FAKE"} else "UNCERTAIN",
                "rationale": _build_rationale(final_label, confidence, hybrid["source"]),
                "claims": _build_claims(text, limit=3),
            },
            "consensus": consensus,
            "hybrid": {
                "source": hybrid["source"],
                "prob_real": hybrid["prob_real"],
                "prob_fake": hybrid["prob_fake"],
                "component_scores": hybrid["scores"],
            },
            "raw_results": [
                {"label": "REAL", "score": hybrid["prob_real"]},
                {"label": "FAKE", "score": hybrid["prob_fake"]},
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hybrid inference failed: {exc}") from exc


@app.post("/detect-academic")
def detect_academic(payload: DetectRequest) -> dict:
    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

    try:
        chunks = _chunk_text(text)
        if not chunks:
            raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

        outputs = [_hybrid_prob_real(chunk) for chunk in chunks]
        avg_prob_real = float(np.mean([item["prob_real"] for item in outputs]))

        consensus, final_label, confidence = _consensus(avg_prob_real)
        claims = _build_claims(text)

        transformer_scores = [item["scores"].get("transformer") for item in outputs if "transformer" in item["scores"]]
        lstm_scores = [item["scores"].get("lstm") for item in outputs if "lstm" in item["scores"]]

        chunk_scores = {"REAL": avg_prob_real, "FAKE": 1.0 - avg_prob_real}
        if transformer_scores:
            chunk_scores["transformer_avg_prob_real"] = float(np.mean(transformer_scores))
        if lstm_scores:
            chunk_scores["lstm_avg_prob_real"] = float(np.mean(lstm_scores))

        return {
            "mode": "academic",
            "model_used": "hybrid-transformer-lstm",
            "prediction": final_label,
            "confidence": confidence,
            "consensus": consensus,
            "claims": claims,
            "evidence_prompts": _build_evidence_prompts(claims),
            "limitations": [
                "Model output is probabilistic and may reflect training data bias.",
                "Long texts are chunked; cross-sentence context may be lost.",
                "No external sources are fetched; evidence must be verified separately.",
                "Predictions can be sensitive to paraphrasing or missing context.",
            ],
            "llm": {
                "label": final_label if final_label in {"REAL", "FAKE"} else "UNCERTAIN",
            },
            "raw_results": [
                {"label": "REAL", "score": avg_prob_real},
                {"label": "FAKE", "score": 1.0 - avg_prob_real},
            ],
            "chunk_scores": chunk_scores,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hybrid academic inference failed: {exc}") from exc
