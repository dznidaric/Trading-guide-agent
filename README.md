# AI Financial Assistant

Short documentation. See **VERCEL_DEPLOYMENT.md** for deployment.

## What it is

**Next.js** chat UI + **FastAPI** + **LangChain/LangGraph** agent for trading, investing, and markets. Non-finance questions are politely declined (`helpers/agent.py`).

## Features

- **Finance-only scope** — SSE `POST /api/chat` 
- **TradingView tools** — `helpers/tradingview_tools.py` + `tradingview-mcp-main/`
- **Mock trades** — `execute_trade` in `helpers/trading_tools.py`; prices from `tradingview-ta`
- **Chat persistence** — `lib/chat-storage.ts` (browser localStorage)
- **Optional Redis** — `REDIS_URL` for LangGraph checkpoints

## Setup

```bash
npm install
uv sync   # or: pip install -r requirements.txt
cp env.example .env   # set OPENAI_API_KEY minimum
```

## Run locally

```bash
# Terminal 1 — API (port 8000)
uv run uvicorn api.index:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
npm run dev
```

Configure API URL via `env.example` and `lib/api.ts`.

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | **Required** |
| `TAVILY_API_KEY` | Optional — `web_search` tool |
| `REDIS_URL` | Optional — server-side conversation state |
| `TRADING212_MODE` | `mock` (default) or `live` |
| `LANGCHAIN_API_KEY` | Optional — LangSmith tracing |

See **`env.example`** for full list.

## Project structure

```
app/, components/     # Next.js UI
api/index.py          # FastAPI + SSE
helpers/
  agent.py            # System prompt & tools
  trading_tools.py    # Trading212 mock + execute_trade
  tradingview_tools.py
lib/                  # API client, chat data, localStorage
```

## Disclaimer

Educational tooling only — not investment, tax, or legal advice. Mock trades use no real funds.

## More

- **`api/README.md`** — API notes
- **`tradingview-mcp-main/README.md`** — TradingView MCP docs

`tradingview-mcp-main/` retains its own license.
