# Fake News Detector Backend

A FastAPI backend for detecting fake news using a BERT-based transformer model.

## Setup Instructions

### 1. First Time Setup

```powershell
# Navigate to the backend directory
cd fake-news-backend

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

The `.env` file should contain your Hugging Face token:

```
HF_TOKEN=your_huggingface_token_here
```

If the `.env` file is missing or empty, the server will fail to start.

### 3. Starting the Server

```powershell
cd fake-news-backend
uvicorn main:app --reload
```

The server will start on `http://127.0.0.1:8000`

**First run note:** The first time you run the app, it will download the BERT model (~500MB+). This may take a few minutes. Subsequent runs will be faster as the model is cached locally.

## API Endpoints

### Health Check
- **GET** `/health`
- Returns: `{"status": "ok", "model": "dhruvpal/fake-news-bert"}`

### Fake News Detection (Real Model)
- **POST** `/detect`
- Body: `{ "text": "Your news text here..." }`
- Returns: Prediction with confidence score
- **Note:** Text must be at least 20 characters

### Fake News Detection (Test Mode)
- **POST** `/detect-test`
- Body: `{ "text": "Your news text here..." }`
- Returns: Mock results (for testing without model)
- Useful for testing your frontend

## Testing with PowerShell

```powershell
# Test with real model
$Body = @{ text = "This is definitely fake news that needs to be tested right now for the application" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/detect" -Method Post -Body $Body -ContentType "application/json" -TimeoutSec 60

# Test with mock endpoint
$Body = @{ text = "This is a test" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/detect-test" -Method Post -Body $Body -ContentType "application/json"
```

## Troubleshooting

### "Model not loaded" error
- The model may still be downloading. Wait a moment and try again.
- Check that you have enough disk space (~1GB)

### "HF_TOKEN missing" error
- Ensure `.env` file exists in the `fake-news-backend` directory
- The file should contain: `HF_TOKEN=your_token`

### Slow first request
- First inference can take 30+ seconds as the model loads
- Subsequent requests will be much faster

## Dependencies

- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Transformers**: Hugging Face transformer models
- **Torch**: PyTorch (required by transformers)
- **Pydantic**: Data validation
- **Python-dotenv**: Environment variable loading
