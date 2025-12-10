# app/services/news_signal_service.py

from __future__ import annotations
import json
import textwrap
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from google.genai import Client
from app.models.news import News
from app.services.sector_service import SectorService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini Async Client
client = Client(api_key=settings.GEMINI_API_KEY).aio


@dataclass
class NewsSignal:
    news_id: int
    tickers: List[str]
    impact_label: str
    impact_confidence: float
    impact_summary: str
    topics: List[str] | None = None


# ----------------------------------------------
# Fallback ticker detection
# ----------------------------------------------
def detect_tickers_from_text(text: str) -> List[str]:
    text_upper = text.upper()

    mapping = {
        "BANK OF BARODA": "BANKBARODA.NS", #Banking stocks 
        "BOB": "BANKBARODA.NS",
        "AXIS BANK": "AXISBANK.NS",
        "AXIS": "AXISBANK.NS",
        "KOTAK": "KOTAKBANK.NS",
        "KOTAK BANK": "KOTAKBANK.NS",
        "ICICI": "ICICIBANK.NS",
        "ICICI BANK": "ICICIBANK.NS",
        "HDFC BANK": "HDFCBANK.NS",
        "HDFC": "HDFCBANK.NS",
        "SBI": "SBIN.NS",
        "STATE BANK OF INDIA": "SBIN.NS",
        "PNB": "PNB.NS",
        "PUNJAB NATIONAL BANK": "PNB.NS",
        "CANARA": "CANBK.NS",
        "CANARA BANK": "CANBK.NS",
        "IDBI": "IDBI.NS",
        "IDFC": "IDFC.NS",
        "IDFC FIRST": "IDFCFIRSTB.NS",
        "IDFC FIRST BANK": "IDFCFIRSTB.NS",
        "YES BANK": "YESBANK.NS",
        "YES": "YESBANK.NS",
        "INDUSIND": "INDUSINDBK.NS",
        "INDUSIND BANK": "INDUSINDBK.NS",
        "BANDHAN": "BANDHANBNK.NS",
        "BANDHAN BANK": "BANDHANBNK.NS",
        "FEDERAL BANK": "FEDERALBNK.NS",
        "RBL BANK": "RBLBANK.NS",
        "RBL": "RBLBANK.NS",
        "UNION BANK": "UNIONBANK.NS",
        "UCO BANK": "UCOBANK.NS",
        "INDIAN BANK": "INDIANB.NS",
        "JK BANK": "J&KBANK.NS",
        "KARUR VYSYA": "KARURVYSYA.NS",
        "CUB": "CUB.NS",
        "CITY UNION BANK": "CUB.NS",
        "MUTHOOT": "MUTHOOTFIN.NS",
        "MUTHOOT FINANCE": "MUTHOOTFIN.NS",
        "MANAPPURAM": "MANAPPURAM.NS",
        "BAJAJ FINANCE": "BAJFINANCE.NS",
        "BAJFIN": "BAJFINANCE.NS",
        "BAJAJ FINSERV": "BAJAJFINSV.NS",
        "SBILIFE": "SBILIFE.NS",
        "HDFC LIFE": "HDFCLIFE.NS",
        "ICICI PRU": "ICICIPRULI.NS",
        "HDFC AMC": "HDFCAMC.NS",
        "TCS": "TCS.NS", #IT sector stocks
        "TATA CONSULTANCY": "TCS.NS",
        "INFOSYS": "INFY.NS",
        "INFY": "INFY.NS",
        "WIPRO": "WIPRO.NS",
        "WIPRO LTD": "WIPRO.NS",
        "HCL": "HCLTECH.NS",
        "HCL TECHNOLOGIES": "HCLTECH.NS",
        "TECH MAHINDRA": "TECHM.NS",
        "TECHM": "TECHM.NS",
        "LTIMINDTREE": "LTIM.NS",
        "LTIM": "LTIM.NS",
        "PERSISTENT": "PERSISTENT.NS",
        "MPHASIS": "MPHASIS.NS",
        "COFORGE": "COFORGE.NS",
        "KPIT": "KPITTECH.NS",
        "KPIT TECHNOLOGIES": "KPITTECH.NS",
        "SONATA": "SONATSOFTW.NS",
        "SONATA SOFTWARE": "SONATSOFTW.NS",
        "TANLA": "TANLA.NS",
        "TANLA SOLUTIONS": "TANLA.NS",
        "RATEGAIN": "RATEGAIN.NS",
        "RATEGAIN TRAVEL": "RATEGAIN.NS",
        "AIRTEL": "BHARTIARTL.NS",
        "BHARTI AIRTEL": "BHARTIARTL.NS",
        "VODAFONE IDEA": "IDEA.NS",
        "VI": "IDEA.NS",
        "JIO FIN": "JIOFIN.NS",
        "JIO FINANCIAL": "JIOFIN.NS",
        "INFO EDGE": "NAUKRI.NS",
        "NAUKRI": "NAUKRI.NS",
        "ZOMATO": "ZOMATO.NS",
        "PAYTM": "PAYTM.NS",
        "NYKAA": "NYKAA.NS",
        "DELHIVERY": "DELHIVERY.NS",
        "IRCTC": "IRCTC.NS",
        "MAPMYINDIA": "MAPMYINDIA.NS",
        "FLIPKART": "WMT",  # Parent Walmart (India not listed)
        "INDIAMART": "INDIAMART.NS",
        "AXISCADES": "AXISCADES.NS",
        "SASKEN": "SASKEN.NS",
        "SUBEX": "SUBEXLTD.NS",
        "ORACLE FINANCIAL": "OFSS.NS",
        "OFSS": "OFSS.NS",
        "RELIANCE": "RELIANCE.NS", # Energy & Oil stocks
        "RIL": "RELIANCE.NS",
        "ONGC": "ONGC.NS",
        "OIL INDIA": "OIL.NS",
        "IOC": "IOC.NS",
        "INDIAN OIL": "IOC.NS",
        "BPCL": "BPCL.NS",
        "BHARAT PETROLEUM": "BPCL.NS",
        "HPCL": "HINDPETRO.NS",
        "HINDUSTAN PETROLEUM": "HINDPETRO.NS",
        "PETRONET LNG": "PETRONET.NS",
        "PETRONET": "PETRONET.NS",
        "GSPL": "GSPL.NS",
        "GAIL": "GAIL.NS",
        "EXIDE": "EXIDEIND.NS",
        "AMARA RAJA": "AMARAJABAT.NS",
        "AMARA RAJA BATTERY": "AMARAJABAT.NS",
        "NTPC": "NTPC.NS", #Power & Renewables stocks
        "TATA POWER": "TATAPOWER.NS",
        "ADANI ENERGY": "ADANIENT.NS",
        "ADANI GREEN": "ADANIGREEN.NS",
        "ADANI TRANSMISSION": "ADANIENERGY.NS",  # New NSE code
        "ADANI POWER": "ADANIPOWER.NS",
        "POWERGRID": "POWERGRID.NS",
        "JSW ENERGY": "JSWENERGY.NS",
        "CESC": "CESC.NS",
        "NHPC": "NHPC.NS",
        "SJVN": "SJVN.NS",
        "JSW STEEL": "JSWSTEEL.NS", #Metals & Mining stocks
        "TATA STEEL": "TATASTEEL.NS",
        "HINDALCO": "HINDALCO.NS",
        "VEDANTA": "VEDL.NS",
        "SAIL": "SAIL.NS",
        "NMDC": "NMDC.NS",
        "COAL INDIA": "COALINDIA.NS",
        "KIOCL": "KIOCL.NS",
        "MOIL": "MOIL.NS",
        "JINDAL STEEL": "JINDALSTEL.NS",
        "JINDAL": "JINDALSTEL.NS",
        "APL APOLLO": "APLAPOLLO.NS",
        "GRAVITA": "GRAVITA.NS",
        "HIND ZINC": "HZL.NS",
        "HZL": "HZL.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
        "TAMO": "TATAMOTORS.NS",
        "MARUTI": "MARUTI.NS",
        "MARUTI SUZUKI": "MARUTI.NS",
        "MAHINDRA": "M&M.NS",
        "M&M": "M&M.NS",
        "HERO": "HEROMOTOCO.NS",
        "HEROMOTO": "HEROMOTOCO.NS",
        "TVS": "TVSMOTOR.NS",
        "TVSMOTOR": "TVSMOTOR.NS",
        "BAJAJ AUTO": "BAJAJ-AUTO.NS",
        "BAJAJAUTO": "BAJAJ-AUTO.NS",
        "ASHOK LEYLAND": "ASHOKLEY.NS",
        "ASHOKLEY": "ASHOKLEY.NS",
        "EICHER": "EICHERMOT.NS",
        "ROYAL ENFIELD": "EICHERMOT.NS",
        "BHARAT FORGE": "BHARATFORG.NS",
        "APOLLO TYRES": "APOLLOTYRE.NS",
        "GOODYEAR": "GOODYEAR.NS",
        "MRF": "MRF.NS",
        "CEAT": "CEATLTD.NS",
        "EXIDE": "EXIDEIND.NS",
        "EXIDE INDUSTRIES": "EXIDEIND.NS",
        "AMARA RAJA": "AMARAJABAT.NS",
        "ARBL": "AMARAJABAT.NS",
        "SUVEN": "SUVENPHAR.NS",
        "Olectra": "OLECTRA.NS",
        "OLECTRA GREENTECH": "OLECTRA.NS",
        "SML ISUZU": "SMLISUZU.NS",
        "ISUZU": "SMLISUZU.NS",
        "ENDURANCE": "ENDURANCE.NS",
        "SUNDRAM": "SUNDRMFAST.NS",
        "VARROC": "VARROC.NS",
        "MOTHERSUMI": "MOTHERSON.NS",
        "MOTHERSON": "MOTHERSON.NS",
        "INDIGO": "INDIGO.NS",
        "INTERGLOBE": "INDIGO.NS",
        "SPICEJET": "SPICEJET.NS",
        "FRANKLIN TEMPLETON": "FLY.NS",  # (example aviation services company)
        "GLOBAL VECTRA": "GLOBALVECT.NS",
        "INDIAN HOTELS": "INDHOTEL.NS",
        "TAJ HOTELS": "INDHOTEL.NS",
        "TAJ": "INDHOTEL.NS",
        "LEMON TREE": "LEMONTREE.NS",
        "LEMONTREE": "LEMONTREE.NS",
        "EIH": "EIHOTEL.NS",
        "OBEROI": "EIHOTEL.NS",
        "CHALET": "CHALET.NS",
        "ROYAL ORCHID": "ROHLTD.NS",
        "ROYAL ORCHID HOTELS": "ROHLTD.NS",
        # Tourism, IRCTC & travel services
        "IRCTC": "IRCTC.NS",
        "YATRA": "YATRA.NS",
        "THOMAS COOK": "THOMASCOOK.NS",
        "THOMASCOOK": "THOMASCOOK.NS",
        "ADANI PORTS": "ADANIPORTS.NS",
        "ADANIPORT": "ADANIPORTS.NS",
        "SHIPPING CORP": "SCI.NS",
        "SCI": "SCI.NS",
        "SEAMEC": "SEAMECLTD.NS",
    }

    return list({sym for name, sym in mapping.items() if name in text_upper})


# ----------------------------------------------
async def fetch_unenriched_news(db: AsyncSession, *, limit: int = 10) -> List[News]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    q = (
        select(News)
        .where(News.processed_at.isnot(None))
        .where((News.impact_label.is_(None)) | (func.cardinality(News.tickers) == 0))
        .where(News.published_at >= cutoff)
        .order_by(News.processed_at.desc())
        .limit(limit)
    )
    return (await db.execute(q)).scalars().all() #type:ignore


# ----------------------------------------------
def build_llm_prompt(news_batch: List[News]) -> str:
    items = [
        {
            "id": n.id,
            "headline": n.title or "",
            "snippet": (n.content or "")[:600],
        }
        for n in news_batch
    ]

    return textwrap.dedent(f"""
You are an AI Indian stock market analyst.

Return STRICT JSON ONLY:
{{
  "results": [
    {{
      "id": <news_id>,
      "tickers": ["RELIANCE.NS"],
      "impact_label": "bullish" | "bearish" | "neutral" | "uncertain",
      "impact_confidence": 0.0 - 1.0,
      "impact_summary": "Short 1-sentence impact",
      "topics": []
    }}
  ]
}}

Rules:
- Use ONLY valid Indian tickers (<SYMBOL>.NS)
- If no confidence → tickers: [], impact_label="uncertain", confidence=0.5
- NO markdown, NO backticks, NO text outside JSON

News batch:
{json.dumps(items, indent=2)}
    """).strip()


# ----------------------------------------------
async def call_llm_for_signals(prompt: str) -> dict:
    try:
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()  # type: ignore

        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))

    except Exception as e:
        logger.error(f"Gemini error: {e}")

    return {}


# ----------------------------------------------
def parse_llm_signals(raw: Dict[str, Any]) -> List[NewsSignal]:
    results = raw.get("results", [])
    return [
        NewsSignal(
            news_id=int(r["id"]),
            tickers=[t.upper() for t in (r.get("tickers") or [])],
            impact_label=r.get("impact_label", "uncertain"),
            impact_confidence=float(r.get("impact_confidence") or 0.5),
            impact_summary=r.get("impact_summary", ""),
            topics=r.get("topics", []),
        )
        for r in results if r.get("id")
    ]


# ----------------------------------------------
async def enrich_news_batch(db: AsyncSession, *, batch_size: int = 10) -> int:
    news_batch = await fetch_unenriched_news(db, limit=batch_size)
    if not news_batch:
        return 0

    prompt = build_llm_prompt(news_batch)
    parsed = await call_llm_for_signals(prompt)
    signals = parse_llm_signals(parsed)

    updated_count = 0

    for sig in signals:
        news = next((n for n in news_batch if n.id == sig.news_id), None)  # type: ignore
        if not news:
            continue

        text = f"{news.title or ''} {news.content or ''}"

        # Merge LLM + Auto tickers
        merged = set(news.tickers or []) | set(sig.tickers) # type: ignore
        fallback = detect_tickers_from_text(text)
        if fallback:
            new_added = set(fallback) - merged
            if new_added:
                logger.info(f"📌 Auto-added {new_added} for news ID {news.id}")
            merged |= set(fallback)

        news.tickers = list(merged) # type: ignore
        news.impact_label = sig.impact_label # type: ignore
        news.impact_confidence = sig.impact_confidence  # type: ignore
        news.impact_summary = sig.impact_summary # type: ignore
        news.topics = sig.topics # type: ignore 
        news.processed_at = datetime.now(timezone.utc)  # type: ignore

        if merged:
            sector = await SectorService.map_tickers_to_sector(db, list(merged))
            if sector:
                news.sector_id = sector # type: ignore

        db.add(news)
        updated_count += 1

    if updated_count:
        await db.commit()

    logger.info(f"✨ Enriched {updated_count} news records")
    return updated_count

# --------------------------------------------------------
# Spotlight Signals API (Trending / High-Confidence Feed)
# --------------------------------------------------------
async def get_spotlight_signals(
    db: AsyncSession,
    *,
    min_confidence: float = 0.6,
    max_hours: int = 48,
    limit: int = 20,
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)

    q = (
        select(News)
        .where(News.impact_confidence >= min_confidence)
        .where(func.cardinality(News.tickers) > 0)
        .where(News.published_at >= cutoff)
        .order_by(News.processed_at.desc())
        .limit(limit)
    )

    items = (await db.execute(q)).scalars().all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "tickers": n.tickers,
            "sentiment": n.sentiment_score,
            "impact_label": n.impact_label,
            "impact_confidence": n.impact_confidence,
            "impact_summary": n.impact_summary,
            "topics": n.topics,
            "published_at": n.published_at,
            "image_url": n.image_url,
        }
        for n in items
    ]
