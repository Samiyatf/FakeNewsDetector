# Hybrid Fake News API (Demo)

This is a third backend for side-by-side comparison with your other two APIs.

## What it does
- Loads **Transformer** model (Hugging Face) and your **LSTM** artifacts.
- Combines both scores into a hybrid probability.
- Keeps endpoint format compatible with your frontend.

## Endpoints
- `GET /health`
- `POST /detect`
- `POST /detect-academic`

## Model inputs
By default this folder expects artifacts in project root:
- `../Trained_Model.keras`
- `../tokenizer.pkl`

You can override with environment vars in `hybrid fake news/.env`:
- `HF_TOKEN=...`
- `TRANSFORMER_MODEL_ID=hamzab/roberta-fake-news-classification`
- `LSTM_MODEL_PATH=...`
- `LSTM_TOKENIZER_PATH=...`
- `LSTM_MAX_LEN=300`
- `LSTM_THRESHOLD=0.5`
- `HYBRID_WEIGHT_TRANSFORMER=0.6`
- `HYBRID_WEIGHT_LSTM=0.4`
- `HYBRID_REAL_THRESHOLD=0.62`
- `HYBRID_FAKE_THRESHOLD=0.38`

## Run
```powershell
cd "hybrid fake news"
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

## Compare all 3 backends
- Backend A: `fake-news-backend` (LSTM-focused) on `8000`
- Backend B: `FakeNewsDetector/api-test-files` (Transformer-focused) on `8001`
- Backend C: `hybrid fake news` (Hybrid) on `8002`

Then send the same text to all three `/detect` endpoints.

### PowerShell comparison chart
```powershell
cd "hybrid fake news"
.\compare-apis.ps1 -Text "Scientists say this headline is misleading because no evidence was provided."
```

Academic mode chart:
```powershell
.\compare-apis.ps1 -Text "Scientists say this headline is misleading because no evidence was provided." -Academic
```

### HTML to test the Hybrid API
Open `hybrid fake news/test-hybrid.html` in Live Server or browser while the hybrid API is running on port `8002`.

### HTML to compare all 3 APIs in one page
Open `hybrid fake news/compare-web.html` in Live Server, paste an article once, and click **Run Comparison**.
It calls:
- `8000` (LSTM test backend)
- `8001` (Transformer backend)
- `8002` (Hybrid backend)
