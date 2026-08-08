"""Market data providers: FMP → Alpha Vantage → mock.

Avoids flaky Yahoo/yfinance rate limits for local testing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MOCK_QUOTES: dict[str, dict[str, Any]] = {
    "AAPL": {"price": 211.56, "previous_close": 212.94, "currency": "USD", "market_cap": 3.18e12, "name": "Apple Inc"},
    "MSFT": {"price": 449.23, "previous_close": 446.29, "currency": "USD", "market_cap": 3.34e12, "name": "Microsoft Corp"},
    "NVDA": {"price": 134.82, "previous_close": 130.61, "currency": "USD", "market_cap": 3.29e12, "name": "NVIDIA Corp"},
    "TSLA": {"price": 318.74, "previous_close": 327.88, "currency": "USD", "market_cap": 1.02e12, "name": "Tesla Inc"},
    "AMZN": {"price": 196.41, "previous_close": 194.79, "currency": "USD", "market_cap": 2.07e12, "name": "Amazon.com"},
    "GOOGL": {"price": 182.33, "previous_close": 181.59, "currency": "USD", "market_cap": 2.24e12, "name": "Alphabet Inc"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sym(symbol: str) -> str:
    return symbol.upper().strip()


def _base_mock(symbol: str) -> dict[str, Any]:
    key = _sym(symbol)
    if key in _MOCK_QUOTES:
        return dict(_MOCK_QUOTES[key])
    seed = sum(ord(c) for c in key) or 100
    price = round(50 + (seed % 400) + (seed % 97) / 100, 2)
    prev = round(price * (1 - ((seed % 7) - 3) / 100), 2)
    return {
        "price": price,
        "previous_close": prev,
        "currency": "USD",
        "market_cap": float(seed) * 1e9,
        "name": f"{key} Corp",
    }


def _fmp_key() -> str:
    return os.getenv("FMP_API_KEY", "").strip()


def _av_key() -> str:
    return os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()


def _get_json(url: str, params: dict[str, Any] | None = None, timeout: float = 12.0) -> Any:
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def fetch_quote(symbol: str) -> dict[str, Any]:
    """Return a normalized quote dict. Sets mock=True only for fallback."""
    symbol = _sym(symbol)
    errors: list[str] = []

    # 1) Financial Modeling Prep
    if _fmp_key():
        try:
            data = _get_json(
                f"https://financialmodelingprep.com/api/v3/quote/{symbol}",
                {"apikey": _fmp_key()},
            )
            if isinstance(data, list) and data:
                row = data[0]
                price = float(row.get("price") or 0)
                prev = float(row.get("previousClose") or row.get("previous_close") or price)
                if price > 0:
                    change = price - prev
                    pct = (change / prev * 100) if prev else float(row.get("changesPercentage") or 0)
                    return {
                        "symbol": symbol,
                        "name": row.get("name") or symbol,
                        "price": round(price, 4),
                        "previous_close": round(prev, 4),
                        "change": round(change, 4),
                        "change_percent": round(pct, 4),
                        "volume": row.get("volume"),
                        "market_cap": row.get("marketCap"),
                        "currency": "USD",
                        "provider": "fmp",
                        "mock": False,
                        "as_of": _now(),
                    }
            errors.append("FMP empty quote")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"FMP: {exc}")

    # 2) Alpha Vantage
    if _av_key():
        try:
            data = _get_json(
                "https://www.alphavantage.co/query",
                {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": _av_key(),
                },
            )
            q = (data or {}).get("Global Quote") or {}
            price = float(q.get("05. price") or 0)
            prev = float(q.get("08. previous close") or price)
            if price > 0:
                change = float(q.get("09. change") or (price - prev))
                pct_raw = str(q.get("10. change percent") or "0").replace("%", "")
                pct = float(pct_raw or 0)
                return {
                    "symbol": symbol,
                    "name": symbol,
                    "price": round(price, 4),
                    "previous_close": round(prev, 4),
                    "change": round(change, 4),
                    "change_percent": round(pct, 4),
                    "volume": int(float(q.get("06. volume") or 0)),
                    "market_cap": None,
                    "currency": "USD",
                    "provider": "alpha_vantage",
                    "mock": False,
                    "as_of": _now(),
                }
            errors.append("Alpha Vantage empty quote")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Alpha Vantage: {exc}")

    # 3) Mock fallback
    reason = "; ".join(errors) if errors else "no provider configured"
    base = _base_mock(symbol)
    price = float(base["price"])
    prev = float(base["previous_close"])
    change = price - prev
    pct = (change / prev * 100) if prev else 0.0
    logger.warning("[MOCK] quote(%s): %s", symbol, reason)
    return {
        "symbol": symbol,
        "name": base.get("name") or symbol,
        "price": price,
        "previous_close": prev,
        "change": round(change, 4),
        "change_percent": round(pct, 4),
        "volume": None,
        "market_cap": base.get("market_cap"),
        "currency": base.get("currency", "USD"),
        "provider": "mock",
        "mock": True,
        "mock_tag": "[MOCK]",
        "mock_reason": reason,
        "as_of": _now(),
        "note": f"[MOCK] fetch_quote failed live call: {reason}",
    }


def fetch_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        if not symbol:
            continue
        out[_sym(symbol)] = fetch_quote(symbol)
    return out


def fetch_history(symbol: str, limit: int = 30) -> dict[str, Any]:
    symbol = _sym(symbol)
    errors: list[str] = []

    if _fmp_key():
        try:
            data = _get_json(
                f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}",
                {"timeseries": limit, "apikey": _fmp_key()},
            )
            hist = (data or {}).get("historical") or []
            if hist:
                rows = []
                for row in reversed(hist[:limit]):
                    rows.append(
                        {
                            "date": row.get("date"),
                            "open": row.get("open"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "close": row.get("close"),
                            "volume": row.get("volume"),
                        }
                    )
                return {
                    "symbol": symbol,
                    "period": f"{limit}d",
                    "bars": rows,
                    "provider": "fmp",
                    "mock": False,
                }
            errors.append("FMP empty history")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"FMP history: {exc}")

    if _av_key():
        try:
            data = _get_json(
                "https://www.alphavantage.co/query",
                {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "compact",
                    "apikey": _av_key(),
                },
            )
            series = (data or {}).get("Time Series (Daily)") or {}
            if series:
                rows = []
                for date, row in list(sorted(series.items()))[-limit:]:
                    rows.append(
                        {
                            "date": date,
                            "open": float(row.get("1. open")),
                            "high": float(row.get("2. high")),
                            "low": float(row.get("3. low")),
                            "close": float(row.get("4. close")),
                            "volume": float(row.get("5. volume")),
                        }
                    )
                return {
                    "symbol": symbol,
                    "period": f"{limit}d",
                    "bars": rows,
                    "provider": "alpha_vantage",
                    "mock": False,
                }
            errors.append("Alpha Vantage empty history")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Alpha Vantage history: {exc}")

    reason = "; ".join(errors) if errors else "no provider configured"
    quote = fetch_quote(symbol)
    price = float(quote["price"])
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(limit, 0, -1):
        close = round(price * (1 - i * 0.002 + ((i % 5) - 2) * 0.001), 2)
        rows.append(
            {
                "date": (now - timedelta(days=i)).date().isoformat(),
                "open": round(close * 0.995, 2),
                "high": round(close * 1.01, 2),
                "low": round(close * 0.99, 2),
                "close": close,
                "volume": 1_000_000 + i * 10_000,
            }
        )
    logger.warning("[MOCK] history(%s): %s", symbol, reason)
    return {
        "symbol": symbol,
        "period": f"{limit}d",
        "bars": rows,
        "provider": "mock",
        "mock": True,
        "mock_tag": "[MOCK]",
        "mock_reason": reason,
        "note": f"[MOCK] fetch_history failed live call: {reason}",
    }


def fetch_fundamentals(symbol: str) -> dict[str, Any]:
    symbol = _sym(symbol)
    errors: list[str] = []

    if _fmp_key():
        try:
            profile = _get_json(
                f"https://financialmodelingprep.com/api/v3/profile/{symbol}",
                {"apikey": _fmp_key()},
            )
            metrics = _get_json(
                f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{symbol}",
                {"apikey": _fmp_key()},
            )
            p = profile[0] if isinstance(profile, list) and profile else {}
            m = metrics[0] if isinstance(metrics, list) and metrics else {}
            if p or m:
                return {
                    "symbol": symbol,
                    "shortName": p.get("companyName"),
                    "sector": p.get("sector"),
                    "industry": p.get("industry"),
                    "trailingPE": m.get("peRatioTTM") or p.get("pe"),
                    "priceToBook": m.get("pbRatioTTM"),
                    "profitMargins": None,
                    "returnOnEquity": m.get("roeTTM"),
                    "revenueGrowth": None,
                    "debtToEquity": m.get("debtToEquityTTM"),
                    "dividendYield": p.get("lastDiv"),
                    "recommendationKey": None,
                    "targetMeanPrice": None,
                    "marketCap": p.get("mktCap"),
                    "provider": "fmp",
                    "mock": False,
                }
            errors.append("FMP empty fundamentals")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"FMP fundamentals: {exc}")

    if _av_key():
        try:
            data = _get_json(
                "https://www.alphavantage.co/query",
                {"function": "OVERVIEW", "symbol": symbol, "apikey": _av_key()},
            )
            if data and data.get("Symbol"):
                return {
                    "symbol": symbol,
                    "shortName": data.get("Name"),
                    "sector": data.get("Sector"),
                    "industry": data.get("Industry"),
                    "trailingPE": _to_float(data.get("PERatio")),
                    "forwardPE": _to_float(data.get("ForwardPE")),
                    "priceToBook": _to_float(data.get("PriceToBookRatio")),
                    "profitMargins": _to_float(data.get("ProfitMargin")),
                    "returnOnEquity": _to_float(data.get("ReturnOnEquityTTM")),
                    "revenueGrowth": _to_float(data.get("QuarterlyRevenueGrowthYOY")),
                    "debtToEquity": None,
                    "dividendYield": _to_float(data.get("DividendYield")),
                    "recommendationKey": None,
                    "targetMeanPrice": _to_float(data.get("AnalystTargetPrice")),
                    "provider": "alpha_vantage",
                    "mock": False,
                }
            errors.append("Alpha Vantage empty overview")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Alpha Vantage overview: {exc}")

    reason = "; ".join(errors) if errors else "no provider configured"
    quote = fetch_quote(symbol)
    logger.warning("[MOCK] fundamentals(%s): %s", symbol, reason)
    return {
        "symbol": symbol,
        "shortName": f"{symbol} [MOCK]",
        "sector": "Technology",
        "industry": "Software",
        "trailingPE": 28.5,
        "forwardPE": 24.1,
        "priceToBook": 8.2,
        "profitMargins": 0.22,
        "returnOnEquity": 0.31,
        "revenueGrowth": 0.12,
        "earningsGrowth": 0.09,
        "debtToEquity": 45.0,
        "dividendYield": 0.004,
        "recommendationKey": "hold",
        "targetMeanPrice": round(float(quote["price"]) * 1.08, 2),
        "provider": "mock",
        "mock": True,
        "mock_tag": "[MOCK]",
        "mock_reason": reason,
        "note": f"[MOCK] fetch_fundamentals failed live call: {reason}",
    }


def fetch_technicals(symbol: str) -> dict[str, Any]:
    hist = fetch_history(symbol, limit=60)
    bars = hist.get("bars") or []
    closes = [float(b["close"]) for b in bars if b.get("close") is not None]
    if len(closes) < 5:
        quote = fetch_quote(symbol)
        last = float(quote["price"])
        return {
            "symbol": _sym(symbol),
            "last_close": last,
            "sma20": round(last * 0.98, 2),
            "sma50": round(last * 0.95, 2),
            "ema12": round(last * 0.99, 2),
            "rsi14": 54.2,
            "trend_hint": "neutral",
            "provider": hist.get("provider", "mock"),
            "mock": True,
            "mock_tag": "[MOCK]",
            "note": "[MOCK] insufficient history for technicals",
        }

    last = closes[-1]
    sma20 = sum(closes[-20:]) / min(20, len(closes))
    sma50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 20 else sma20

    # EMA12
    ema = closes[0]
    k = 2 / (12 + 1)
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)

    # RSI14 rough
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    window = gains[-14:]
    loss_w = losses[-14:]
    avg_gain = sum(window) / len(window) if window else 0
    avg_loss = sum(loss_w) / len(loss_w) if loss_w else 1e-9
    rs = avg_gain / (avg_loss or 1e-9)
    rsi = 100 - (100 / (1 + rs))

    return {
        "symbol": _sym(symbol),
        "last_close": last,
        "sma20": round(sma20, 4),
        "sma50": round(sma50, 4),
        "ema12": round(ema, 4),
        "rsi14": round(rsi, 2),
        "trend_hint": "bullish" if sma20 > sma50 else "bearish" if sma20 < sma50 else "neutral",
        "provider": hist.get("provider"),
        "mock": bool(hist.get("mock")),
        "mock_tag": hist.get("mock_tag"),
        "mock_reason": hist.get("mock_reason"),
    }


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, "None", "-", ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_market_cap(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if n >= 1e12:
        return f"{n / 1e12:.2f}T"
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    if n >= 1e6:
        return f"{n / 1e6:.2f}M"
    return f"{n:.0f}"


def format_volume(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}K"
    return f"{n:.0f}"
