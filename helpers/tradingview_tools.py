"""
tradingview_tools.py — TradingView MCP tools integration for LangChain agent.

Wraps TradingView MCP server functions as LangChain tools for use in the financial assistant.
"""

import logging
import os
import sys
import json
from pathlib import Path
from typing import Any

from langchain.tools import tool

# Add TradingView MCP source to Python path
_mcp_path = Path(__file__).parent.parent / "mcp" / "tradingview-mcp-main" / "src"
if str(_mcp_path) not in sys.path:
    sys.path.insert(0, str(_mcp_path))

logger = logging.getLogger("alpha-guide.tradingview")

# Try to import TradingView MCP functions
try:
    from tradingview_mcp.server import (
        top_gainers,
        top_losers,
        bollinger_scan,
        rating_filter,
        coin_analysis,
        consecutive_candles_scan,
        advanced_candle_pattern,
        volume_breakout_scanner,
        volume_confirmation_analysis,
        smart_volume_scanner,
    )
    TRADINGVIEW_AVAILABLE = True
    logger.info("TradingView MCP tools loaded successfully")
except ImportError as e:
    TRADINGVIEW_AVAILABLE = False
    logger.warning(f"TradingView MCP tools not available: {e}")
    # Create dummy functions to prevent import errors
    def _dummy_function(*args, **kwargs):
        return {"error": "TradingView MCP tools not installed. Install tradingview-screener and tradingview-ta packages."}
    
    top_gainers = top_losers = bollinger_scan = rating_filter = coin_analysis = _dummy_function
    consecutive_candles_scan = advanced_candle_pattern = volume_breakout_scanner = _dummy_function
    volume_confirmation_analysis = smart_volume_scanner = _dummy_function


def _format_tradingview_response(result: Any) -> str:
    """Format TradingView tool response as a readable string."""
    if isinstance(result, dict):
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format coin analysis
        if "price_data" in result:
            return _format_coin_analysis(result)
        
        # Format pattern analysis
        if "pattern_type" in result or "data" in result:
            return _format_pattern_analysis(result)
        
        # Format volume analysis
        if "volume_analysis" in result:
            return _format_volume_analysis(result)
        
        # Generic dict formatting
        return json.dumps(result, indent=2, default=str)
    
    elif isinstance(result, list):
        if not result:
            return "No results found."
        
        # Format list of coins/symbols
        formatted = []
        for i, item in enumerate(result[:20], 1):  # Limit to 20 for readability
            if isinstance(item, dict):
                symbol = item.get("symbol", "Unknown")
                change = item.get("changePercent", 0)
                indicators = item.get("indicators", {})
                
                line = f"{i}. {symbol}: {change:+.2f}%"
                if "RSI" in indicators:
                    line += f" (RSI: {indicators['RSI']:.1f})"
                if "close" in indicators:
                    line += f" | Price: ${indicators['close']:.6f}"
                
                formatted.append(line)
            else:
                formatted.append(f"{i}. {item}")
        
        if len(result) > 20:
            formatted.append(f"\n... and {len(result) - 20} more results")
        
        return "\n".join(formatted)
    
    else:
        return str(result)


def _tv_empty_response_error(message: str) -> bool:
    """True when TradingView scan returned empty/invalid JSON (common for some daily feeds)."""
    if not message:
        return False
    return any(
        x in message
        for x in ("Expecting value", "line 1 column 1", "JSONDecodeError", "invalid data")
    )


def _format_coin_analysis(result: dict) -> str:
    """Format coin analysis result."""
    lines = []

    note = result.get("data_source_note")
    if note:
        lines.append(f"Note: {note}")
        lines.append("")

    symbol = result.get("symbol", "Unknown")
    exchange = result.get("exchange", "Unknown")
    timeframe = result.get("timeframe", "Unknown")
    
    lines.append(f"📊 Analysis: {symbol} ({exchange}, {timeframe})")
    lines.append("")
    
    # Price data
    price_data = result.get("price_data", {})
    if price_data:
        lines.append("💰 Price Data:")
        lines.append(f"  Current: ${price_data.get('current_price', 0):.6f}")
        if "change_percent" in price_data:
            change = price_data["change_percent"]
            lines.append(f"  Change: {change:+.2f}%")
        if "high" in price_data and "low" in price_data:
            lines.append(f"  High: ${price_data['high']:.6f} | Low: ${price_data['low']:.6f}")
        lines.append("")
    
    # Bollinger analysis
    bb_analysis = result.get("bollinger_analysis", {})
    if bb_analysis:
        lines.append("📈 Bollinger Bands:")
        rating = bb_analysis.get("rating", 0)
        signal = bb_analysis.get("signal", "NEUTRAL")
        bbw = bb_analysis.get("bbw", 0)
        lines.append(f"  Rating: {rating} ({signal})")
        lines.append(f"  BBW: {bbw:.4f}")
        lines.append("")
    
    # Technical indicators
    tech = result.get("technical_indicators", {})
    if tech:
        lines.append("🔧 Technical Indicators:")
        if "rsi" in tech:
            rsi = tech["rsi"]
            rsi_signal = tech.get("rsi_signal", "Neutral")
            lines.append(f"  RSI: {rsi:.2f} ({rsi_signal})")
        if "sma20" in tech:
            lines.append(f"  SMA20: ${tech['sma20']:.6f}")
        if "ema50" in tech:
            lines.append(f"  EMA50: ${tech['ema50']:.6f}")
        if "macd" in tech:
            lines.append(f"  MACD: {tech['macd']:.6f}")
        lines.append("")
    
    # Market sentiment
    sentiment = result.get("market_sentiment", {})
    if sentiment:
        lines.append("📊 Market Sentiment:")
        lines.append(f"  Overall: {sentiment.get('overall_rating', 0)}")
        lines.append(f"  Signal: {sentiment.get('buy_sell_signal', 'NEUTRAL')}")
        lines.append(f"  Volatility: {sentiment.get('volatility', 'Unknown')}")
    
    return "\n".join(lines)


def _format_pattern_analysis(result: dict) -> str:
    """Format pattern analysis result."""
    lines = []
    
    pattern_type = result.get("pattern_type", "unknown")
    total_found = result.get("total_found", 0)
    data = result.get("data", [])
    
    lines.append(f"🕯️ Pattern Analysis: {pattern_type.upper()}")
    lines.append(f"Total found: {total_found}")
    lines.append("")
    
    for i, item in enumerate(data[:10], 1):  # Limit to 10
        symbol = item.get("symbol", "Unknown")
        change = item.get("current_change", item.get("change", 0))
        lines.append(f"{i}. {symbol}: {change:+.2f}%")
    
    if len(data) > 10:
        lines.append(f"\n... and {len(data) - 10} more")
    
    return "\n".join(lines)


def _format_volume_analysis(result: dict) -> str:
    """Format volume analysis result."""
    lines = []
    
    symbol = result.get("symbol", "Unknown")
    lines.append(f"📊 Volume Analysis: {symbol}")
    lines.append("")
    
    volume_analysis = result.get("volume_analysis", {})
    if volume_analysis:
        lines.append("📈 Volume:")
        lines.append(f"  Current: {volume_analysis.get('current_volume', 0):,}")
        lines.append(f"  Ratio: {volume_analysis.get('volume_ratio', 0):.2f}x")
        lines.append(f"  Strength: {volume_analysis.get('volume_strength', 'Unknown')}")
        lines.append("")
    
    signals = result.get("signals", [])
    if signals:
        lines.append("🚦 Signals:")
        for signal in signals[:5]:  # Limit to 5
            lines.append(f"  {signal}")
    
    return "\n".join(lines)


# LangChain tool wrappers
@tool
async def tradingview_top_gainers(exchange: str = "KUCOIN", timeframe: str = "15m", limit: int = 25) -> str:
    """Get top gainers (highest performing assets) from TradingView.
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, NASDAQ, NYSE, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M)
        limit: Maximum number of results to return (default: 25, max: 50)
    
    Returns:
        Formatted list of top gainers with price changes and indicators.
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = top_gainers(exchange=exchange, timeframe=timeframe, limit=limit)
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_top_gainers: {e}")
        return f"Error fetching top gainers: {str(e)}"


@tool
async def tradingview_top_losers(exchange: str = "KUCOIN", timeframe: str = "15m", limit: int = 25) -> str:
    """Get top losers (biggest declining assets) from TradingView.
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, NASDAQ, NYSE, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M)
        limit: Maximum number of results to return (default: 25, max: 50)
    
    Returns:
        Formatted list of top losers with price changes and indicators.
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = top_losers(exchange=exchange, timeframe=timeframe, limit=limit)
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_top_losers: {e}")
        return f"Error fetching top losers: {str(e)}"


@tool
async def tradingview_bollinger_scan(
    exchange: str = "KUCOIN", 
    timeframe: str = "4h", 
    bbw_threshold: float = 0.04, 
    limit: int = 50
) -> str:
    """Scan for assets with tight Bollinger Bands (squeeze detection - potential breakout candidates).
    
    This tool finds assets where the Bollinger Band Width (BBW) is low, indicating a squeeze pattern that often precedes significant price movements. Lower BBW values mean tighter bands and higher breakout potential.
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, NASDAQ, NYSE, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M)
        bbw_threshold: Maximum Bollinger Band Width to filter (lower = tighter bands, default: 0.04). Values below 0.03 indicate very tight bands.
        limit: Maximum number of results to return (default: 50, max: 100)
    
    Returns:
        Formatted list of assets with tight Bollinger Bands ready for potential breakouts, including symbol, price change, and technical indicators.
    
    Example usage: "Find coins with tight Bollinger Bands on KuCoin" or "Scan for Bollinger squeeze on 4h timeframe"
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = bollinger_scan(exchange=exchange, timeframe=timeframe, bbw_threshold=bbw_threshold, limit=limit)
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_bollinger_scan: {e}")
        return f"Error scanning Bollinger Bands: {str(e)}"


@tool
async def tradingview_rating_filter(
    exchange: str = "KUCOIN", 
    timeframe: str = "5m", 
    rating: int = 2, 
    limit: int = 25
) -> str:
    """Filter assets by Bollinger Band rating (-3 to +3).
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M)
        rating: BB rating (-3=Strong Sell, -2=Sell, -1=Weak Sell, 0=Neutral, 1=Weak Buy, 2=Buy, 3=Strong Buy)
        limit: Maximum number of results to return (default: 25, max: 50)
    
    Returns:
        Formatted list of assets matching the specified rating.
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = rating_filter(exchange=exchange, timeframe=timeframe, rating=rating, limit=limit)
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_rating_filter: {e}")
        return f"Error filtering by rating: {str(e)}"


@tool
async def tradingview_coin_analysis(
    symbol: str,
    exchange: str = "KUCOIN",
    timeframe: str = "15m"
) -> str:
    """Get comprehensive technical analysis for a specific asset.
    
    Args:
        symbol: Asset symbol (e.g., "BTCUSDT", "AAPL", "ETHUSDT", "SHEL")
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, NASDAQ, NYSE, LSE, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M). If the daily (or other) feed returns empty
            from TradingView, the tool retries once with **5m** intraday and states that in the output.
    
    Returns:
        Detailed technical analysis including price data, Bollinger Bands, RSI, MACD, and other indicators.
    
    Note: For LSE stocks, if you get an error, try:
    - Using a different exchange if the stock is dual-listed (e.g., NASDAQ, NYSE)
    - Verifying the symbol exists on TradingView
    - Some LSE symbols may require different formatting
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    _INTRADAY_FALLBACK_TF = "5m"

    def _run_coin_analysis(tf: str) -> Any:
        return coin_analysis(symbol=symbol, exchange=exchange, timeframe=tf)

    try:
        requested_tf = (timeframe or "15m").strip()
        logger.info(
            "Calling coin_analysis: symbol=%s, exchange=%s, timeframe=%s",
            symbol,
            exchange,
            requested_tf,
        )
        result = _run_coin_analysis(requested_tf)

        if isinstance(result, dict) and "error" in result:
            error_msg = result.get("error", "Unknown error")
            logger.warning("coin_analysis returned error: %s", error_msg)
            if (
                (
                    _tv_empty_response_error(error_msg)
                    or "No data found" in error_msg
                )
                and requested_tf.lower() != _INTRADAY_FALLBACK_TF.lower()
            ):
                logger.info(
                    "Retrying coin_analysis with %s intraday (requested %s failed)",
                    _INTRADAY_FALLBACK_TF,
                    requested_tf,
                )
                result = _run_coin_analysis(_INTRADAY_FALLBACK_TF)
                if isinstance(result, dict) and "error" not in result and "price_data" in result:
                    result = {
                        **result,
                        "data_source_note": (
                            f"The {requested_tf} TradingView feed returned empty or invalid data; "
                            f"the figures below use the **{_INTRADAY_FALLBACK_TF}** intraday feed instead."
                        ),
                    }
                elif isinstance(result, dict) and "error" in result:
                    error_msg = result["error"]

            if isinstance(result, dict) and "error" in result:
                error_msg = result.get("error", "Unknown error")
                if _tv_empty_response_error(error_msg):
                    return (
                        f"TradingView returned invalid/empty data for {symbol} on {exchange} "
                        f"(tried {requested_tf} and {_INTRADAY_FALLBACK_TF}).\n\n"
                        "Try: NASDAQ/NYSE for US stocks, verify the ticker, or retry later."
                    )
                return f"Error analyzing {symbol} on {exchange}: {error_msg}"

        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception("Error in tradingview_coin_analysis: %s", e)
        error_str = str(e)
        if _tv_empty_response_error(error_str):
            return (
                f"Error analyzing {symbol} on {exchange}: TradingView returned invalid/empty data. "
                f"Try NASDAQ/NYSE for US equities or another timeframe."
            )
        return f"Error analyzing {symbol}: {error_str}"


@tool
async def tradingview_volume_breakout(
    exchange: str = "KUCOIN",
    timeframe: str = "15m",
    volume_multiplier: float = 2.0,
    price_change_min: float = 3.0,
    limit: int = 25
) -> str:
    """Detect assets with volume breakout combined with price breakout.
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h, 1D, 1W, 1M)
        volume_multiplier: How many times the volume should be above normal (default: 2.0)
        price_change_min: Minimum price change percentage (default: 3.0)
        limit: Maximum number of results to return (default: 25, max: 50)
    
    Returns:
        Formatted list of assets with volume and price breakouts.
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = volume_breakout_scanner(
            exchange=exchange,
            timeframe=timeframe,
            volume_multiplier=volume_multiplier,
            price_change_min=price_change_min,
            limit=limit
        )
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_volume_breakout: {e}")
        return f"Error scanning volume breakouts: {str(e)}"


@tool
async def tradingview_candle_pattern(
    exchange: str = "KUCOIN",
    timeframe: str = "15m",
    pattern_type: str = "bullish",
    candle_count: int = 3,
    min_growth: float = 2.0,
    limit: int = 20
) -> str:
    """Scan for assets with consecutive bullish or bearish candle patterns.
    
    Args:
        exchange: Exchange name (KUCOIN, BINANCE, BYBIT, etc.)
        timeframe: Time interval (5m, 15m, 1h, 4h)
        pattern_type: "bullish" (growing candles) or "bearish" (shrinking candles)
        candle_count: Number of consecutive candles to check (2-5, default: 3)
        min_growth: Minimum growth percentage for each candle (default: 2.0)
        limit: Maximum number of results to return (default: 20, max: 50)
    
    Returns:
        Formatted list of assets with consecutive candle patterns.
    """
    if not TRADINGVIEW_AVAILABLE:
        return "TradingView tools are not available. Please install tradingview-screener and tradingview-ta packages."
    
    try:
        result = consecutive_candles_scan(
            exchange=exchange,
            timeframe=timeframe,
            pattern_type=pattern_type,
            candle_count=candle_count,
            min_growth=min_growth,
            limit=limit
        )
        return _format_tradingview_response(result)
    except Exception as e:
        logger.exception(f"Error in tradingview_candle_pattern: {e}")
        return f"Error scanning candle patterns: {str(e)}"


# Export all tools
__all__ = [
    "tradingview_top_gainers",
    "tradingview_top_losers",
    "tradingview_bollinger_scan",
    "tradingview_rating_filter",
    "tradingview_coin_analysis",
    "tradingview_volume_breakout",
    "tradingview_candle_pattern",
    "TRADINGVIEW_AVAILABLE",
]
