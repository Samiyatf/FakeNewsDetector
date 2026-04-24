# inCredibleAI: Fake News Detector

A dual-model NLP system that classifies news articles as real or fake using both a custom LSTM model and a transformer-based RoBERTa API. The project focuses on how model performance shifts under distribution changes, particularly with AI-generated text.

## Overview

This system was built to explore a core challenge in misinformation detection: models can perform well on static datasets but fail when exposed to new writing styles or AI-generated content.

Two approaches were implemented and evaluated:

- A custom-trained LSTM model for pattern-based classification  
- A RoBERTa-based API for context-aware inference  

The project emphasizes not just model accuracy, but understanding failure modes and real-world limitations.

<p align="center">
  <img src="https://github.com/user-attachments/assets/5bc447dd-bc58-4a0e-a4c3-8a8c915d4e41" width="700" />
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/d00083d3-7736-4319-b875-bcd8d3bd8daa" width="700" />
</p>

## Key Features

- Binary classification of news articles (real vs fake)  
- Dual-model architecture (LSTM + RoBERTa)  
- End-to-end NLP pipeline (preprocessing → training → inference)  
- Real-time prediction via API integration  
- Evaluation across in-distribution and out-of-distribution data  
- Explicit analysis of model weaknesses

## How It Works

- User inputs article text  
- LSTM model processes sequence patterns  
- RoBERTa model provides contextual prediction  
- System compares outputs and returns final classification + confidence  

## Tech Stack

- Python  
- TensorFlow / Keras (LSTM)  
- Hugging Face Transformers (RoBERTa)  
- FastAPI + Uvicorn  
- Pandas, NumPy, Scikit-learn  
- JavaScript (frontend integration)  
- Visual Studio Code  

## System Design

- Frontend captures user input and sends requests to backend  
- FastAPI backend routes input to the RoBERTa model for inference  
- LSTM model is trained separately on structured datasets  
- Predictions are returned with confidence scores  
- System supports both offline evaluation and real-time usage  

## Machine Learning Approach

### LSTM Model

- Trained on 45,000+ labeled articles (Kaggle Fake & Real News)  
- Input limited to 300 tokens per sample  
- Learns stylistic and structural patterns in text  
- Outputs binary classification (Real = 0, Fake = 1)  

### RoBERTa Model

- Pre-trained transformer (`hamzab/roberta-fake-news-classification`)  
- Fine-tuned for fake news detection tasks  
- Captures semantic and contextual relationships in text  
- Used for real-time inference via API  

## Results

### LSTM Performance

- ~98% accuracy on Kaggle dataset  
- Drops to ~81% on mixed dataset (real + AI-generated fake news)  

**Key Insight:**  
The LSTM model generalizes poorly when the data distribution shifts. High accuracy on training-like data does not translate to robustness.

### RoBERTa Performance

- Consistently high-confidence predictions (>85%)  
- Better performance on unseen and complex text  
- Still produces false positives  

**Limitation:**  
The model detects linguistic patterns, not factual correctness.

## System Workflow

1. Load and preprocess labeled datasets  
2. Tokenize and normalize text  
3. Train LSTM model on structured data  
4. Integrate RoBERTa via API for inference  
5. Evaluate models on multiple datasets  
6. Predict new input text  

## Getting Started

### 1. Clone the Repository
git clone https://github.com/Samiyatf/FakeNewsDetector.git  
cd FakeNewsDetector  

### 2. Install Dependencies
pip install pandas numpy scikit-learn nltk tensorflow transformers fastapi uvicorn  

### 3. Download NLTK Data
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

### 4. Run the Project
python main.py  

### 5. Run API
uvicorn main:app --reload  

## Key Takeaways

- Model performance is highly dependent on data distribution  
- High accuracy can mask poor generalization  
- Transformer models improve robustness but are not perfect  
- Evaluating failure cases is critical in ML systems  

## Future Work

- Domain adaptation for AI-generated content  
- Larger and more diverse datasets  
- Explainability (highlighting model reasoning)  
- Integration with fact-checking APIs  
- Full-article processing without chunking  

## Authors

- Samiya Fyffe — Product & Program Management, system design, code review, and UI direction  
- Miles Brower — LSTM model development, training, and code review  
- Dante Grante — RoBERTa integration and frontend development  
- Temiloluwa Okelowo — LSTM Testing, Data preprocessing and dataset preparation
- Sharnae Roye — Frontend development  

Advisor: Dr. Mulham Fawakherji  

---

This project focuses on building and evaluating NLP systems under real-world constraints, with an emphasis on understanding model behavior beyond surface-level accuracy.
