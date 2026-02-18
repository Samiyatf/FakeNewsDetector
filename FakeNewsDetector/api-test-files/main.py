import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
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
        results = classifier(text, truncation=True, max_length=512)
        logger.info(f"Inference results received: {results}")

        # results should be a list with one dict: [{"label": "...", "score": 0.xx}]
        if not isinstance(results, list) or len(results) == 0:
            raise ValueError("Unexpected results format from model")

        top = results[0]
        prediction = top.get("label", "UNKNOWN").upper()
        confidence = float(top.get("score", 0))
        
        # Create signals based on confidence
        signals = []
        if confidence > 0.8:
            signals.append({"type": "score", "text": "High confidence prediction", "impact": 0.25})
        elif confidence > 0.6:
            signals.append({"type": "score", "text": "Moderate confidence", "impact": 0.15})
        else:
            signals.append({"type": "score", "text": "Low confidence - verify independently", "impact": 0.1})
        
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
        sentences = text.split('.')
        claims = [s.strip()[:300] for s in sentences if len(s.strip()) > 20][:3]
        if not claims:
            claims = ["Verify: " + text[:150]]

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
