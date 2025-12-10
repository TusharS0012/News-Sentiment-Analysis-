import yfinance as yf
from datetime import datetime


def fetch_from_yahoo():
    try:
        news=yf.Ticker("^NSEI").news
        print("Fetched Yahoo news")
        return news[:3] if news else []
    except Exception:
        return []
    

if __name__ == "__main__":
    news = fetch_from_yahoo()
    print(news)    