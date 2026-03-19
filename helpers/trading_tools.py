"""
trading_tools.py — Broker integration and trade execution for the financial assistant.

Provides a mock Trading212 client for test environments and a LangChain `execute_trade` tool.
Swap `MockTrading212Client` for `Trading212RestClient` when wiring the real REST API.

Design:
- **Trading212Client** (ABC): contract for place_order.
- **MockTrading212Client**: simulates fills using TradingView (tradingview_ta): **1D** close first, then **5m** if daily is empty.
- **get_trading212_client()**: factory reading TRADING212_MODE (mock | live).

Request correlation:
- **chat_thread_id** (contextvars): set by FastAPI before agent streaming so trade logs
  can be tied to a conversation without passing thread_id through the LLM.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

logger = logging.getLogger("alpha-guide.trading")

# ---------------------------------------------------------------------------
# Per-request context (set from api/index.py during /api/chat streaming)
# ---------------------------------------------------------------------------
chat_thread_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "chat_thread_id", default=None
)


def set_chat_thread_context(thread_id: str) -> contextvars.Token[str | None]:
    """Bind conversation thread_id for the current async task. Call reset_chat_thread_context in finally."""
    return chat_thread_id.set(thread_id)


def reset_chat_thread_context(token: contextvars.Token[str | None]) -> None:
    """Restore previous thread_id after the request completes."""
    chat_thread_id.reset(token)


OrderSide = Literal["BUY", "SELL"]
OrderStatus = Literal["FILLED", "REJECTED", "PENDING"]


@dataclass
class PlaceOrderResult:
    """Normalized order response (mock or live API)."""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    status: OrderStatus
    exchange: str
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    currency: str = "USD"
    is_simulated: bool = True
    raw_response: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class Trading212Client(ABC):
    """Contract for Trading212 (or compatible) execution. Subclass for REST."""

    exchange_name: str = "TRADING212"

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        *,
        order_type: str = "MARKET",
    ) -> PlaceOrderResult:
        """Submit an order. order_type is e.g. MARKET, LIMIT (live API may support more)."""
        ...


# ---------------------------------------------------------------------------
# Reference price for mock fills — TradingView via tradingview_ta (no hardcoded prices)
# ---------------------------------------------------------------------------
def _tv_screener_for_exchange_prefix(prefix: str) -> str:
    """Map TradingView exchange prefix to screener id used by tradingview_ta."""
    p = prefix.strip().lower()
    mapping = {
        "nasdaq": "america",
        "nyse": "america",
        "amex": "america",
        "lse": "europe",
        "xetra": "europe",
        "euronext": "europe",
        "binance": "crypto",
        "kucoin": "crypto",
        "coinbase": "crypto",
        "bybit": "crypto",
        "okx": "crypto",
        "bitget": "crypto",
        "gateio": "crypto",
        "huobi": "crypto",
    }
    return mapping.get(p, "america")


def _tv_price_candidates(raw_symbol: str) -> list[tuple[str, str]]:
    """Return (screener, FULL_SYMBOL) pairs to try with get_multiple_analysis."""
    s = raw_symbol.strip().upper().replace(" ", "")
    if ":" in s:
        ex, _tick = s.split(":", 1)
        scr = _tv_screener_for_exchange_prefix(ex)
        return [(scr, s)]
    candidates: list[tuple[str, str]] = [
        ("america", f"NASDAQ:{s}"),
        ("america", f"NYSE:{s}"),
        ("europe", f"LSE:{s}"),
    ]
    if s.endswith("USDT") or s.endswith("USD") or "BTC" in s or "ETH" in s:
        candidates.extend(
            [
                ("crypto", f"BINANCE:{s}"),
                ("crypto", f"KUCOIN:{s}"),
                ("crypto", f"COINBASE:{s}"),
            ]
        )
        if s.endswith("USD") and not s.endswith("USDT") and len(s) > 3:
            base = s[:-3]
            candidates.extend(
                [
                    ("crypto", f"BINANCE:{base}USDT"),
                    ("crypto", f"COINBASE:{s}"),
                ]
            )
    return candidates


def _fetch_tv_close_sync(screener: str, full_symbol: str) -> float | None:
    """Blocking: reference price from TradingView — try daily, then 5m if daily is empty."""
    try:
        from tradingview_ta import get_multiple_analysis
    except ImportError:
        logger.warning(
            "tradingview_ta is not installed; cannot resolve mock fill price from TradingView"
        )
        return None
    key = full_symbol.upper()
    for interval in ("1D", "5m"):
        try:
            analysis = get_multiple_analysis(
                screener=screener,
                interval=interval,
                symbols=[key],
            )
            row = analysis.get(key)
            if row is None:
                continue
            close = row.indicators.get("close")
            if close is not None and float(close) > 0:
                if interval == "5m":
                    logger.debug(
                        "Mock fill: using %s close (daily empty) for %s",
                        interval,
                        full_symbol,
                    )
                return float(close)
        except Exception as e:
            logger.debug(
                "TradingView price lookup failed for %s (%s) %s: %s",
                full_symbol,
                screener,
                interval,
                e,
            )
    return None


def _resolve_reference_price_from_tradingview(symbol: str) -> tuple[float, str] | None:
    """Try candidates until one returns a daily close. Returns (price, tradingview_symbol)."""
    for screener, full in _tv_price_candidates(symbol):
        price = _fetch_tv_close_sync(screener, full)
        if price is not None:
            return (price, full)
    return None


class MockTrading212Client(Trading212Client):
    """
    Simulates Trading212 REST behaviour without calling the real broker API.

    - Mock fill price from TradingView (``tradingview_ta``): daily close, or **5m** intraday if daily fails.
    - Tries NASDAQ/NYSE/LSE and common crypto venues until a quote resolves.
    - Generates UUID order IDs, small async delay, structured JSON logs per attempt.
    """

    exchange_name = "TRADING212"

    def __init__(self, fill_delay_seconds: float = 0.08) -> None:
        self._fill_delay = fill_delay_seconds

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        *,
        order_type: str = "MARKET",
    ) -> PlaceOrderResult:
        if quantity <= 0:
            result = PlaceOrderResult(
                order_id="",
                symbol=symbol.upper(),
                side=side,
                quantity=Decimal(str(quantity)),
                status="REJECTED",
                exchange=self.exchange_name,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                is_simulated=True,
                error_message="Quantity must be positive",
            )
            self._log_attempt(result, order_type=order_type)
            return result

        await asyncio.sleep(self._fill_delay)

        resolved = await asyncio.to_thread(_resolve_reference_price_from_tradingview, symbol)
        if resolved is None:
            result = PlaceOrderResult(
                order_id="",
                symbol=symbol.upper(),
                side=side,
                quantity=Decimal(str(quantity)),
                status="REJECTED",
                exchange=self.exchange_name,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                is_simulated=True,
                error_message=(
                    "Could not fetch a reference price from TradingView for this symbol. "
                    "Try a full TradingView symbol (e.g. NASDAQ:AAPL, BINANCE:BTCUSDT) or "
                    "verify the ticker with tradingview_coin_analysis."
                ),
            )
            self._log_attempt(result, order_type=order_type)
            return result

        base, tv_symbol = resolved
        slip = 0.0005 if side == "BUY" else -0.0005
        avg_price = round(base * (1 + slip), 4)
        oid = f"T212-MOCK-{uuid.uuid4().hex[:12].upper()}"

        result = PlaceOrderResult(
            order_id=oid,
            symbol=symbol.upper(),
            side=side,
            quantity=Decimal(str(quantity)),
            status="FILLED",
            exchange=self.exchange_name,
            filled_quantity=Decimal(str(quantity)),
            average_fill_price=Decimal(str(avg_price)),
            is_simulated=True,
            raw_response={
                "mode": "mock",
                "order_type": order_type,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "reference_price_source": "tradingview",
                "tradingview_symbol": tv_symbol,
                "reference_close_1d": base,
            },
        )
        self._log_attempt(result, order_type=order_type)
        return result

    def _log_attempt(self, result: PlaceOrderResult, *, order_type: str) -> None:
        """Structured log for every trade attempt (review / audit)."""
        thread = chat_thread_id.get()
        payload = {
            "event": "trade_attempt",
            "thread_id": thread,
            "exchange": result.exchange,
            "order_id": result.order_id or None,
            "symbol": result.symbol,
            "side": result.side,
            "quantity": str(result.quantity),
            "status": result.status,
            "filled_quantity": str(result.filled_quantity),
            "average_fill_price": str(result.average_fill_price)
            if result.average_fill_price
            else None,
            "is_simulated": result.is_simulated,
            "order_type": order_type,
            "error": result.error_message,
        }
        logger.info("trading212_mock %s", json.dumps(payload, default=str))


class Trading212RestClient(Trading212Client):
    """
    Placeholder for real Trading212 REST integration.

    When implementing:
    - Use official API docs for auth (API key / OAuth) and base URL.
    - Map responses into PlaceOrderResult.
    - Never log secrets or full account numbers.
    """

    def __init__(self, api_base_url: str | None = None, api_key: str | None = None) -> None:
        self._base = api_base_url or os.getenv("TRADING212_API_BASE_URL", "")
        self._api_key = api_key or os.getenv("TRADING212_API_KEY", "")

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        *,
        order_type: str = "MARKET",
    ) -> PlaceOrderResult:
        raise NotImplementedError(
            "Trading212RestClient.place_order is not implemented. "
            "Use TRADING212_MODE=mock or implement HTTP calls per Trading212 API docs."
        )


def get_trading212_client() -> Trading212Client:
    """
    Factory: TRADING212_MODE=live uses Trading212RestClient (must be implemented);
    any other value (default mock) uses MockTrading212Client.
    """
    mode = os.getenv("TRADING212_MODE", "mock").strip().lower()
    if mode == "live":
        return Trading212RestClient()
    return MockTrading212Client()


def _format_order_confirmation(r: PlaceOrderResult) -> str:
    if r.status == "REJECTED":
        return (
            f"Order REJECTED on {r.exchange}: {r.error_message or 'Unknown reason'}\n"
            f"Symbol: {r.symbol}, Side: {r.side}, Qty: {r.quantity}"
        )
    price_txt = f"${r.average_fill_price}" if r.average_fill_price is not None else "n/a"
    sim = " (SIMULATED — no real money)" if r.is_simulated else ""
    return (
        f"Order {r.status} on {r.exchange}{sim}\n"
        f"- Order ID: {r.order_id}\n"
        f"- Symbol: {r.symbol}\n"
        f"- Side: {r.side}\n"
        f"- Quantity: {r.filled_quantity}\n"
        f"- Average fill price: {price_txt}\n"
        f"- Type: {r.raw_response.get('order_type', 'MARKET')}"
    )


@tool
async def execute_trade(
    symbol: str,
    quantity: float,
    order_type: str,
    exchange: str = "TRADING212",
) -> str:
    """
    Execute a trade on the configured broker (Trading212 in test mode uses a mock).

    Use only when the user explicitly wants to place an order. In test mode, execution
    is simulated — no real orders are sent.

    Args:
        symbol: Ticker or TradingView full symbol (e.g. AAPL, NASDAQ:AAPL, BINANCE:BTCUSDT).
            Mock fills use TradingView daily close; ambiguous tickers try NASDAQ, NYSE, LSE, then crypto venues.
        quantity: Number of shares or units (must be positive).
        order_type: BUY or SELL (market-style mock fill).
        exchange: Broker identifier; only TRADING212 is supported in mock mode.

    Returns:
        Human-readable order confirmation or rejection reason.
    """
    side = order_type.strip().upper()
    if side not in ("BUY", "SELL"):
        return f"Invalid order_type '{order_type}'. Use BUY or SELL."

    ex = exchange.strip().upper()
    if ex != "TRADING212":
        return (
            f"Exchange '{exchange}' is not supported in this environment. "
            f"Use TRADING212 (mock execution)."
        )

    if quantity <= 0:
        return "Quantity must be a positive number."

    client = get_trading212_client()
    try:
        result = await client.place_order(
            symbol=symbol,
            quantity=quantity,
            side=side,  # type: ignore[arg-type]
            order_type="MARKET",
        )
        return _format_order_confirmation(result)
    except NotImplementedError as e:
        logger.warning(str(e))
        return f"Live trading is not configured: {e}"
    except Exception as e:
        logger.exception("execute_trade failed")
        return f"Trade execution failed: {e}"


__all__ = [
    "MockTrading212Client",
    "Trading212Client",
    "Trading212RestClient",
    "PlaceOrderResult",
    "execute_trade",
    "get_trading212_client",
    "set_chat_thread_context",
    "reset_chat_thread_context",
    "chat_thread_id",
]
