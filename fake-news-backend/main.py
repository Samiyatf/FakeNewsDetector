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
load_dotenv(dotenv_path=env_path)

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "dhruvpal/fake-news-bert"  # change this if you switch models

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN missing. Put it in a .env file (HF_TOKEN=...).")

# ✅ Initialize the model locally using transformers
logger.info(f"Loading model: {MODEL_ID}")
try:
    from transformers import pipeline
    # Load the fake news detector model locally
    classifier = pipeline("text-classification", model=MODEL_ID)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    classifier = None

app = FastAPI()

# ✅ Allow your frontend to call the backend (adjust ports/domains if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev
        "http://localhost:5173",  # Vite dev
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
        
        # Use the local transformer pipeline
        results = classifier(text)
        logger.info(f"Inference results received: {results}")

        # results should be a list with one dict: [{"label": "...", "score": 0.xx}]
        if not isinstance(results, list) or len(results) == 0:
            raise ValueError("Unexpected results format from model")

        top = results[0]

        return {
            "model_used": MODEL_ID,
            "prediction": top.get("label", "UNKNOWN"),
            "confidence": float(top.get("score", 0)),
            "all_results": results,
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
