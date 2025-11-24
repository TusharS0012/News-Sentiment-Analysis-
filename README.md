# 📈 News Sentiment Trading Backend

An AI-powered backend that ingests real-time financial news, analyzes sentiment using FinBERT, detects relevant sectors via Zero-Shot Learning, and aggregates sector-wise sentiment for trading insights.

---

## 🚀 Features

### 🔍 Real-Time News Ingestion  
- Fetches financial/business news from **Mediastack API**  
- Extracts title, source, content, and timestamps  
- Cleans and stores structured news data in PostgreSQL  

### 🧠 Sentiment Analysis (FinBERT)  
- Uses **FinBERT (ProsusAI/finbert)** via Hugging Face  
- Returns `Positive`, `Negative`, or `Neutral` sentiment  
- Stores sentiment score, label, confidence, and timestamp  

### 🏭 Sector Detection (Zero-Shot Classification)  
Automatically classifies news into sectors such as:

> Finance, Technology, Energy, Pharma, Automobile  

Using **facebook/bart-large-mnli** Zero-Shot Classification (no training required)

### 📊 Sector Sentiment Aggregation  
Computes window-based sector sentiment trends:

| Sector | Avg Sentiment | News Count | Window |
|--------|--------------|------------|--------|
| Finance | 0.32 | 18 | Last 15 min |
| Pharma | -0.45 | 6 | Last 15 min |

### ⏱ Automated Scheduling  
| Task | Frequency |
|------|-----------|
| News Fetching + Sentiment | Every 10 mins |
| Sentiment Aggregation | Every 15 mins |

---

## 🏗 Architecture

┌───────────────┐
│ News Ingestor │──▶ Fetch news ─┐
└───────┬───────┘ ▼
│ ┌────────────────┐
▼ │ PostgreSQL DB │
┌───────────────┐ └────────────────┘
│ FinBERT AI │──▶ Sentiment & Sector
└────────┬──────┘
│
▼
┌─────────────────────────────┐
│ Aggregation Engine │
│ (Sector Sentiment Trends) │
└─────────────────────────────┘


---

## ⚙️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (Async) |
| AI Models | FinBERT, BART-MNLI |
| Task Scheduler | APScheduler |
| HTTP Client | httpx |
| Hosting AI | Hugging Face Inference API |

---

## 📁 Project Structure

📦 News-Sentiment-Backend
┣━━ 📂 app
┃ ┣━━ 📂 ingestion
┃ ┣━━ 📂 sentiment
┃ ┣━━ 📂 models
┃ ┣━━ 📂 services
┃ ┣━━ 📂 analytics
┃ ┣━━ 📂 core
┃ ┗━━ main.py
┣━━ 📂 migrations
┣━━ .env
┣━━ requirements.txt
┗━━ README.md


---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/yourusername/news-sentiment-backend.git
cd news-sentiment-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
Create a .env file in the root:

NEWS_API_KEY=your_mediastack_api_key
HF_API_TOKEN=your_huggingface_api_key
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/newsdb
▶️ Run the Application
uvicorn app.main:app --reload

📡 API Endpoints
Method	Endpoint	Description
GET	/news/	Get recent news
GET	/aggregates/	Get sector sentiment trends
POST	/news/ingest	Ingest news manually
GET	/sectors/	List supported sectors
📊 Sample Output (Aggregated)
[
  {
    "sector_id": 1,
    "sector_name": "Finance",
    "avg_sentiment": 0.265,
    "news_count": 12,
    "window_start": "2025-11-23T23:35:00Z",
    "window_end": "2025-11-23T23:50:00Z"
  }
]

🔮 Future Enhancements

🏦 Stock price integration (Finnhub / Yahoo Finance / NSE API)

📈 Generate Buy/Sell/Hold Signals

🌐 Real-time Trading Dashboard (React / Next.js)

⚡ Faster results with Redis caching

🧠 Named Entity Recognition for tickers and companies

🤝 Contributing

Contributions are welcome!
Please open an issue or submit a pull request 🚀.

⭐ Support

If you like this project, give it a star ⭐ on GitHub and share it!

📜 License

Licensed under the MIT License.
