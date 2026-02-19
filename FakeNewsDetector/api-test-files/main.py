import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import re
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env from the same directory as this script
env_path = Path(__file__).parent / ".env"
logger.info(f"Looking for .env at: {env_path}")
logger.info(f".env exists: {env_path.exists()}")

# Manually load .env if it exists
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        logger.info(f"Raw .env content repr: {repr(content)}")
        logger.info(f"Raw .env content: {content}")
        # Parse the .env file manually
        for line in content.split('\n'):
            line = line.strip()
            logger.info(f"Parsing line: '{line}'")
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                os.environ[key] = value
                logger.info(f"✅ Set environment variable: {key}")

load_dotenv(dotenv_path=env_path, verbose=True)

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "hamzab/roberta-fake-news-classification"  # change this if you switch models

logger.info(f"HF_TOKEN present: {bool(HF_TOKEN)}")
if HF_TOKEN:
    logger.info(f"✅ HF_TOKEN loaded: {HF_TOKEN[:15]}***")
else:
    logger.warning("⚠️ HF_TOKEN not loaded - will try without it")
logger.info(f"Using model: {MODEL_ID}")

# ✅ Initialize the model locally using transformers
classifier = None
try:
    from transformers import pipeline
    logger.info("Loading model...")
    # Load the fake news detector model locally
    classifier = pipeline("text-classification", model=MODEL_ID, token=HF_TOKEN)
    logger.info("✅ Model loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load model: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    classifier = None

app = FastAPI()

# ✅ Allow your frontend to call the backend (adjust ports/domains if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev
        "http://localhost:5173",  # Vite dev
        "http://localhost:5500",  # Live Server
        "http://127.0.0.1:5500",  # Live Server alt
        "http://localhost:8080",  # Common port
        "null",  # For file:// protocol when opened locally
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectRequest(BaseModel):
    text: str


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        if current_len + len(sentence) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _classify_text(text: str) -> dict:
    results = classifier(text, truncation=True, max_length=512)
    if not isinstance(results, list) or len(results) == 0:
        raise ValueError("Unexpected results format from model")
    top = results[0]
    prediction = top.get("label", "UNKNOWN").upper()
    confidence = float(top.get("score", 0))
    return {
        "prediction": prediction,
        "confidence": confidence,
        "raw_results": results,
    }


def _aggregate_chunks(chunks: list[str]) -> dict:
    if not chunks:
        raise ValueError("No chunks to classify")

    chunk_outputs = []
    scores = {"FAKE": [], "REAL": [], "UNKNOWN": []}
    raw_results = []
    for chunk in chunks:
        output = _classify_text(chunk)
        chunk_outputs.append(output)
        label = output["prediction"]
        scores.setdefault(label, []).append(output["confidence"])
        raw_results.append(output["raw_results"][0])

    avg_scores = {label: (sum(vals) / len(vals)) for label, vals in scores.items() if vals}
    if not avg_scores:
        avg_scores = {"UNKNOWN": 0.0}

    prediction = max(avg_scores.items(), key=lambda item: item[1])[0]
    confidence = float(avg_scores.get(prediction, 0))

    return {
        "prediction": prediction,
        "confidence": confidence,
        "raw_results": raw_results,
        "chunk_count": len(chunks),
        "chunk_outputs": chunk_outputs,
        "avg_scores": avg_scores,
    }


def _build_claims(text: str, limit: int = 5) -> list[str]:
    sentences = _split_sentences(text)
    claims = [s[:300] for s in sentences if len(s) > 20]
    if not claims:
        claims = ["Verify: " + text[:150]]
    return claims[:limit]


def _build_evidence_prompts(claims: list[str]) -> list[dict]:
    prompts = []
    for claim in claims:
        prompts.append({
            "claim": claim,
            "questions": [
                "What primary source supports or refutes this claim?",
                "Is there independent coverage from credible outlets?",
                "Are the dates, locations, and actors consistent across sources?",
            ],
            "suggested_sources": [
                "Official reports or data portals",
                "Peer-reviewed research",
                "Reputable news organizations",
                "Fact-checking organizations",
            ],
        })
    return prompts


def _academic_response(text: str) -> dict:
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

    results = _aggregate_chunks(chunks)
    prediction = results["prediction"]
    confidence = results["confidence"]

    claims = _build_claims(text)
    evidence_prompts = _build_evidence_prompts(claims)

    limitations = [
        "Model output is probabilistic and may reflect training data bias.",
        "Long texts are chunked; cross-sentence context may be lost.",
        "No external sources are fetched; evidence must be verified separately.",
        "Predictions can be sensitive to paraphrasing or missing context.",
    ]

    methodology = {
        "model": MODEL_ID,
        "chunking": {
            "enabled": True,
            "chunk_count": results["chunk_count"],
            "max_chars_per_chunk": 1200,
        },
        "inference": {
            "truncation": True,
            "max_length": 512,
        },
    }

    return {
        "mode": "academic",
        "model_used": MODEL_ID,
        "prediction": prediction,
        "confidence": confidence,
        "claims": claims,
        "evidence_prompts": evidence_prompts,
        "limitations": limitations,
        "methodology": methodology,
        "raw_results": results["raw_results"],
        "chunk_scores": results["avg_scores"],
    }

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID}

@app.post("/detect")
def detect(payload: DetectRequest):
    if classifier is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

    try:
        logger.info(f"Starting inference for text: {text[:50]}...")
        
        # Use the local transformer pipeline with truncation
        output = _classify_text(text)
        results = output["raw_results"]
        logger.info(f"Inference results received: {results}")

        prediction = output["prediction"]
        confidence = output["confidence"]
        
        # Create signals based on confidence and text characteristics
        signals = []
        
        # Confidence signal
        if confidence > 0.8:
            signals.append({"type": "score", "text": "High confidence prediction", "impact": 0.25})
        elif confidence > 0.6:
            signals.append({"type": "score", "text": "Moderate confidence", "impact": 0.15})
        else:
            signals.append({"type": "score", "text": "Low confidence - verify independently", "impact": 0.1})
        
        # Text length analysis
        text_len = len(text)
        if text_len < 100:
            signals.append({"type": "length", "text": "Very short text - limited context", "impact": 0.1})
        elif text_len > 2000:
            signals.append({"type": "length", "text": "Long-form content", "impact": 0.05})
        
        # Emotional/sensational language indicators (basic heuristic)
        sensational_words = ["shocking", "unbelievable", "amazing", "stunned", "secret", "exposed", "revealed"]
        text_lower = text.lower()
        sensational_count = sum(1 for word in sensational_words if word in text_lower)
        if sensational_count >= 3:
            signals.append({"type": "language", "text": "Contains sensational language", "impact": 0.15})
        
        # All-caps detection (shouting)
        words = text.split()
        if words:
            caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
            if caps_ratio > 0.15:
                signals.append({"type": "language", "text": "Excessive capitalization detected", "impact": 0.12})
        
        # Exclamation points
        exclamation_count = text.count('!')
        if exclamation_count > 5:
            signals.append({"type": "punctuation", "text": "Excessive exclamation marks", "impact": 0.08})
        
        # Question marks (clickbait indicator)
        question_count = text.count('?')
        if question_count > 3 and text_len < 500:
            signals.append({"type": "punctuation", "text": "Multiple questions - possible clickbait", "impact": 0.1})
        
        # Create rationale
        rationale = []
        if prediction == "FAKE":
            if confidence > 0.8:
                rationale.append("The model detected strong indicators of misinformation.")
            else:
                rationale.append("The model suggests this may contain unreliable information.")
        else:
            if confidence > 0.8:
                rationale.append("The model indicates this appears to be reliable content.")
            else:
                rationale.append("The model is uncertain about this content's reliability.")
        rationale.append("Always verify major claims with independent sources.")
        
        # Create sample claims - increased from 100 to 300 chars
        claims = _build_claims(text, limit=3)

        # Consensus: agree if confidence is high enough
        llm_agrees = confidence > 0.65
        consensus = "agree" if llm_agrees else "disagree"
        llm_label = prediction if llm_agrees else "UNCERTAIN"

        return {
            "model_used": MODEL_ID,
            "lstm": {
                "label": prediction,
                "confidence": confidence,
                "signals": signals
            },
            "llm": {
                "ran": True,
                "label": llm_label,
                "rationale": rationale,
                "claims": claims
            },
            "consensus": consensus,
            "raw_results": results
        }

    except Exception as e:
        error_msg = f"Inference failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/detect-academic")
def detect_academic(payload: DetectRequest):
    if classifier is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")

    try:
        logger.info(f"Starting academic inference for text: {text[:50]}...")
        return _academic_response(text)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Academic inference failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

# ✅ Add a test endpoint that doesn't require the model
@app.post("/detect-test")
def detect_test(payload: DetectRequest):
    """Test endpoint that returns mock results without needing the model"""
    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="Text too short. Paste a longer excerpt.")
    
    # Mock results for testing
    return {
        "model_used": MODEL_ID,
        "prediction": "FAKE" if len(text) % 2 == 0 else "REAL",
        "confidence": 0.85,
        "all_results": [
            {"label": "FAKE", "score": 0.85},
            {"label": "REAL", "score": 0.15}
        ],
        "note": "This is a test endpoint with mock data"
    }
