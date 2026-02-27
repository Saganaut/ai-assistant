"""Market data service — quotes via yfinance, news via RSS (feedparser).

Quotes are fetched from Yahoo Finance (no API key required) and cached for
5 minutes.  News headlines are fetched from configurable RSS feeds and cached
for 10 minutes.
"""

import asyncio
import logging
import time
from typing import Any

import feedparser  # type: ignore[import-untyped]
import yfinance as yf  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Default symbol groups
INDEXES: list[tuple[str, str]] = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "NASDAQ"),
    ("^DJI", "DOW"),
]

MACRO: list[tuple[str, str]] = [
    ("^TNX", "10Y Yield"),
    ("^VIX", "VIX"),
    ("GC=F", "Gold"),
    ("CL=F", "Oil"),
    ("BTC-USD", "Bitcoin"),
]

DEFAULT_WATCHLIST: list[str] = []

DEFAULT_FEEDS: list[str] = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.marketwatch.com/marketwatch/topstories",
]

_QUOTE_TTL = 300   # 5 minutes
_NEWS_TTL = 600    # 10 minutes


class MarketsService:
    """Singleton-friendly service for market quotes and news."""

    def __init__(self) -> None:
        self._quote_cache: dict[str, tuple[dict[str, Any], float]] = {}
        self._news_cache: tuple[list[dict[str, Any]], float] | None = None

    def _fetch_quote(self, symbol: str, label: str | None = None) -> dict[str, Any] | None:
        """Fetch a single quote, returning cached value if fresh."""
        cached = self._quote_cache.get(symbol)
        if cached:
            data, ts = cached
            if time.time() - ts < _QUOTE_TTL:
                return data

        try:
            ticker = yf.Ticker(symbol)
            fi = ticker.fast_info
            price: float | None = fi.last_price
            prev_close: float | None = fi.previous_close
            if price is None or prev_close is None or prev_close == 0:
                return None
            change = round(price - prev_close, 4)
            change_pct = round((change / prev_close) * 100, 2)
            data = {
                "symbol": symbol,
                "name": label or symbol,
                "price": round(price, 4),
                "change": change,
                "change_pct": change_pct,
            }
            self._quote_cache[symbol] = (data, time.time())
            return data
        except Exception as e:
            logger.debug("Quote fetch failed for %s: %s", symbol, e)
            return None

    def _fetch_snapshot(self, watchlist: list[str]) -> dict[str, list[dict[str, Any]]]:
        indexes = [q for sym, name in INDEXES if (q := self._fetch_quote(sym, name))]
        macro = [q for sym, name in MACRO if (q := self._fetch_quote(sym, name))]
        watch = [q for sym in watchlist if (q := self._fetch_quote(sym))]
        return {"indexes": indexes, "macro": macro, "watchlist": watch}

    async def get_snapshot(self, watchlist: list[str]) -> dict[str, Any]:
        return await asyncio.to_thread(self._fetch_snapshot, watchlist)

    def _fetch_news(self, feeds: list[str]) -> list[dict[str, Any]]:
        if self._news_cache:
            articles, ts = self._news_cache
            if time.time() - ts < _NEWS_TTL:
                return articles

        articles: list[dict[str, Any]] = []
        for url in feeds:
            try:
                feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
                source = feed.feed.get("title", url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "")
                    if title and link:
                        articles.append({
                            "title": title,
                            "url": link,
                            "source": source,
                            "published": entry.get("published", ""),
                        })
            except Exception as e:
                logger.debug("News feed failed for %s: %s", url, e)

        articles = articles[:20]
        self._news_cache = (articles, time.time())
        return articles

    async def get_news(self, feeds: list[str]) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_news, feeds)
