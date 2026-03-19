"""
agent.py — LLM, tools, and LangGraph agent for the Alpha-Guide RAG pipeline.

Keeps all LangChain model/prompt/tool construction in one place so the
API layer stays thin.
"""

import logging
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.retrievers import ParentDocumentRetriever
from qdrant_client import QdrantClient
from langgraph.checkpoint.memory import MemorySaver
# Tavily import - optional, gracefully handles if package unavailable
try:
    from tavily import AsyncTavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    AsyncTavilyClient = None  # type: ignore
from helpers.trading_tools import execute_trade
from helpers.tradingview_tools import (
    tradingview_top_gainers,
    tradingview_top_losers,
    tradingview_bollinger_scan,
    tradingview_rating_filter,
    tradingview_coin_analysis,
    tradingview_volume_breakout,
    tradingview_candle_pattern,
    TRADINGVIEW_AVAILABLE,
)

load_dotenv()

logger = logging.getLogger("alpha-guide.agent")

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

# ---------------------------------------------------------------------------
# LangSmith tracing — enabled automatically when LANGCHAIN_API_KEY is set.
# ---------------------------------------------------------------------------
_env_label = os.getenv("ENVIRONMENT", "local")
_langchain_api_key = os.getenv("LANGCHAIN_API_KEY")

if _langchain_api_key:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = f"Alpha Guide - {_env_label}"
    os.environ["LANGSMITH_ENDPOINT"] = "https://eu.api.smith.langchain.com"
    # LANGCHAIN_API_KEY is already in the environment from .env / Vercel
    logger.info("LangSmith tracing enabled → project: Alpha Guide - %s", _env_label)
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    logger.info("LangSmith tracing disabled (LANGCHAIN_API_KEY not set)")
checkpointer = None
agent = None
retriever = None

# Tavily client for web search (initialised lazily if TAVILY_API_KEY is set)
_tavily_client: AsyncTavilyClient | None = None


def get_tavily_client() -> AsyncTavilyClient:
    """Return a singleton Tavily client, raising if the API key is missing or package unavailable."""
    if not TAVILY_AVAILABLE:
        raise RuntimeError("Tavily package is not installed — web search unavailable. Install with: pip install tavily")
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is not set — web search unavailable.")
        _tavily_client = AsyncTavilyClient(api_key=api_key)
    return _tavily_client


RAG_TEMPLATE = """\
You are a specialist assistant for **trading, investing, and financial markets ONLY**.

**STRICT SCOPE - You MUST refuse off-topic requests:**

**IN SCOPE (answer these):**
- Stocks, bonds, ETFs, mutual funds, crypto, commodities, forex, derivatives
- Technical analysis, fundamental analysis, market data, charts, indicators
- Portfolio strategies, risk management, asset allocation
- Economic indicators and news as they relate to investing
- Broker platforms, order types, trading mechanics (educational only)
- Company analysis, earnings, financial statements
- General investment education (not personalized advice)

**OUT OF SCOPE (politely refuse these):**
- Recipes, cooking, food, restaurants
- Entertainment, games, movies, sports (unless about investing in these industries)
- Travel, lifestyle, fitness, health
- Programming, IT, general how-to (unless about trading tools)
- Any topic not directly related to financial markets or investing

**How to handle off-topic requests:**
When a user asks something outside the scope above:
1. Politely decline in 2-3 sentences
2. State you only assist with trading, investing, and financial markets
3. Invite them to ask a finance-related question
4. Do NOT use any tools for off-topic requests

You have access to several tools:

**Knowledge & Research:**
1. **web_search** — search ONLY for finance-related news (markets, companies, economy). Do not use for non-financial topics.

**TradingView Market Analysis Tools (ALWAYS USE THESE FOR MARKET DATA):**
3. **tradingview_top_gainers** — find highest performing assets (stocks, crypto, ETFs) on any exchange. Use for: "show me top gainers", "what's performing well", "best performers"
4. **tradingview_top_losers** — find biggest declining assets on any exchange. Use for: "show me losers", "what's falling", "worst performers"
5. **tradingview_bollinger_scan** — scan for assets with tight Bollinger Bands (squeeze detection - potential breakouts). Use for: "find tight Bollinger Bands", "Bollinger squeeze", "breakout candidates", "low volatility assets". This tool WORKS and should be used when asked about Bollinger Band scans.
6. **tradingview_rating_filter** — filter assets by Bollinger Band rating (-3 to +3: Strong Sell to Strong Buy). Use for: "find buy signals", "strong buy stocks", "oversold assets"
7. **tradingview_coin_analysis** — get comprehensive technical analysis for a specific asset (price, RSI, MACD, Bollinger Bands, etc.). Use for: "analyze BTC", "technical analysis of AAPL", "what are the indicators for ETH"
8. **tradingview_volume_breakout** — detect assets with volume breakout combined with price breakout. Use for: "volume breakouts", "high volume movers", "breakout with volume confirmation"
9. **tradingview_candle_pattern** — scan for assets with consecutive bullish or bearish candle patterns. Use for: "consecutive green candles", "bullish patterns", "candle formations"

**Order execution (Trading212 — test / simulated by default):**
10. **execute_trade** — submit a BUY or SELL order via the configured broker (Trading212). In the default test setup, orders are **simulated** (no real money, no real exchange connectivity). Use **only** when the user clearly asks to place, submit, or execute a trade and has specified symbol, side (buy/sell), and quantity (or you confirm those details with them first). Parameters: `symbol`, `quantity`, `order_type` (BUY or SELL), `exchange` (default TRADING212).

**Guidelines:**
- **CHECK SCOPE FIRST:** Before doing anything, verify the question is about trading/investing/markets. If not, refuse politely without using tools.
- **IMPORTANT:** For in-scope market data, technical analysis, or asset scans, you MUST use the TradingView tools.
- For in-scope market data, ALWAYS use TradingView tools - do not claim you lack access.
- If a TradingView tool fails, try different exchange or timeframe.
- Use web_search ONLY for in-scope finance queries (market news, companies, economy).
- Provide accurate information; cite sources when possible.
- If you don't know an in-scope answer, say so honestly.
- **execute_trade:** Only use when user explicitly requests a trade. Remind users mock mode uses no real money.

**Supported Exchanges:** KUCOIN, BINANCE, BYBIT, BITGET, OKX, COINBASE, GATEIO, HUOBI, BITFINEX, NASDAQ, NYSE, BIST, and more.
**Supported Timeframes:** 5m, 15m, 1h, 4h, 1D, 1W, 1M
"""



@tool
async def web_search(query: str) -> str:
    """Search the web for finance-related information only (market news, companies, economic data).

    The model should NOT invoke this for off-topic user questions.

    Args:
        query: Finance-related search query about markets, companies, or economy.
    """
    try:
        client = get_tavily_client()
        results = await client.search(query=query, max_results=5)
        if not results.get("results"):
            return "No relevant web results found."

        formatted = []
        for i, r in enumerate(results["results"], 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")
            formatted.append(f"[Web {i}] {title}\n{url}\n{content}")

        return "\n\n".join(formatted)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Web search failed: {e}"


# TradingView tools (conditionally added if available)
tradingview_tools = []
if TRADINGVIEW_AVAILABLE:
    tradingview_tools = [
        tradingview_top_gainers,
        tradingview_top_losers,
        tradingview_bollinger_scan,
        tradingview_rating_filter,
        tradingview_coin_analysis,
        tradingview_volume_breakout,
        tradingview_candle_pattern,
    ]
    logger.info(f"TradingView tools enabled: {len(tradingview_tools)} tools available")
    logger.info(f"TradingView tool names: {[tool.name for tool in tradingview_tools]}")
else:
    logger.warning("TradingView tools not available - install tradingview-screener and tradingview-ta")

tools = [web_search, execute_trade] + tradingview_tools
logger.info("Trade execution tool registered: execute_trade (Trading212 mock unless TRADING212_MODE=live)")


async def get_agent():
    """
    Lazily initialise and return the LangGraph agent.

    Uses Redis for checkpointing when REDIS_URL is set, otherwise falls back
    to an in-memory checkpointer (fine for local development).
    """
    global agent, checkpointer
    if agent is None or checkpointer is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                # Production: persist conversation state in Redis
                from langgraph.checkpoint.redis.aio import AsyncRedisSaver

                checkpointer = AsyncRedisSaver(redis_url=redis_url)
                await checkpointer.asetup()
            except Exception as e:
                logger.exception("Failed to set up Redis checkpointer")

        else:
            checkpointer = MemorySaver()

        agent = create_agent(
            model="openai:gpt-5-mini",
            tools=tools,
            system_prompt=RAG_TEMPLATE,
            checkpointer=checkpointer,
        )
    return agent
