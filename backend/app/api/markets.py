"""Markets API — quotes (yfinance) and news headlines (RSS)."""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.integrations.markets import DEFAULT_FEEDS, MarketsService

logger = logging.getLogger(__name__)
router = APIRouter()

_svc = MarketsService()

_WATCHLIST_FILE = settings.data_dir / "markets_watchlist.json"
_FEEDS_FILE = settings.data_dir / "markets_feeds.json"


def _load_watchlist() -> list[str]:
    if _WATCHLIST_FILE.exists():
        try:
            return json.loads(_WATCHLIST_FILE.read_text())
        except Exception:
            pass
    return []


def _save_watchlist(symbols: list[str]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_FILE.write_text(json.dumps(symbols))


def _load_feeds() -> list[str]:
    if _FEEDS_FILE.exists():
        try:
            return json.loads(_FEEDS_FILE.read_text())
        except Exception:
            pass
    return list(DEFAULT_FEEDS)


def _save_feeds(feeds: list[str]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _FEEDS_FILE.write_text(json.dumps(feeds))


# ---------------------------------------------------------------------------
# Snapshot (quotes + news in one call)
# ---------------------------------------------------------------------------

@router.get("/snapshot")
async def markets_snapshot():
    """Return indexes, macro indicators, watchlist quotes, and news headlines."""
    watchlist = _load_watchlist()
    feeds = _load_feeds()
    snapshot, news = await asyncio.gather(
        _svc.get_snapshot(watchlist),
        _svc.get_news(feeds),
    )
    return {**snapshot, "news": news}


# ---------------------------------------------------------------------------
# Watchlist management
# ---------------------------------------------------------------------------

@router.get("/watchlist")
async def get_watchlist():
    return {"watchlist": _load_watchlist()}


class AddSymbolRequest(BaseModel):
    symbol: str


@router.post("/watchlist")
async def add_symbol(req: AddSymbolRequest):
    symbol = req.symbol.strip().upper()
    if not symbol:
        return {"error": "Symbol cannot be empty"}
    watchlist = _load_watchlist()
    if symbol not in watchlist:
        watchlist.append(symbol)
        _save_watchlist(watchlist)
    return {"watchlist": watchlist}


@router.delete("/watchlist/{symbol}")
async def remove_symbol(symbol: str):
    watchlist = _load_watchlist()
    watchlist = [s for s in watchlist if s.upper() != symbol.upper()]
    _save_watchlist(watchlist)
    return {"watchlist": watchlist}


# ---------------------------------------------------------------------------
# News feed management
# ---------------------------------------------------------------------------

@router.get("/feeds")
async def get_feeds():
    return {"feeds": _load_feeds()}


class AddFeedRequest(BaseModel):
    url: str


@router.post("/feeds")
async def add_feed(req: AddFeedRequest):
    url = req.url.strip()
    if not url:
        return {"error": "URL cannot be empty"}
    feeds = _load_feeds()
    if url not in feeds:
        feeds.append(url)
        _save_feeds(feeds)
    return {"feeds": feeds}


@router.delete("/feeds")
async def remove_feed(req: AddFeedRequest):
    url = req.url.strip()
    feeds = _load_feeds()
    feeds = [f for f in feeds if f != url]
    _save_feeds(feeds)
    return {"feeds": feeds}
