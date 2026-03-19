/**
 * api.ts — Backend API client for the Alpha-Guide RAG chatbot.
 *
 * Handles SSE (Server-Sent Events) streaming from the FastAPI backend
 * so the chat UI can display tokens progressively as they arrive.
 *
 * API URL resolution:
 * - Local dev: defaults to http://localhost:8000 (backend runs separately)
 * - Production (Vercel): set NEXT_PUBLIC_API_URL="" (same-origin, backend is serverless function)
 * - Override: set NEXT_PUBLIC_API_URL in .env.local for any custom URL
 */

// Smart default: same-origin for production (Vercel), localhost:8000 for local dev
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "" // Production: same-origin
    : "http://localhost:8000") // Local dev: separate backend process

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface StreamChatOptions {
  /** Which retrieval strategy to use (default: "naive") */
  retriever?: string
  /** Conversation thread ID — must be consistent across messages in
   *  the same conversation so the checkpointer can track history. */
  threadId?: string
  /** Optional context dict forwarded to the agent */
  context?: Record<string, unknown>
  /** Optional config dict forwarded to the agent (e.g. thread_id) */
  config?: Record<string, unknown>
}

/** Discriminated union yielded by `streamChatResponse`. */
export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "status"; status: string }

/** Shape of a complete tool-call inside an AI message. */
interface ToolCall {
  name: string
  args: Record<string, unknown>
  id?: string
  type?: string
}

/** Shape of an incremental tool-call chunk (streamed piece-by-piece). */
interface ToolCallChunk {
  name?: string
  args?: string
  id?: string
  index?: number
}

/** A single parsed SSE message from the LangChain agent stream. */
interface LangChainMessageChunk {
  type: string
  content: string
  /** Fully-assembled tool calls (may be empty on streaming chunks). */
  tool_calls?: ToolCall[]
  /** Incremental tool-call data — present on streaming AIMessageChunks. */
  tool_call_chunks?: ToolCallChunk[]
  /** Present on ToolMessage responses. */
  name?: string
}

/**
 * Map tool names to short, user-friendly status labels.
 * Falls back to "Calling tool…" for unknown tools.
 */
const TOOL_STATUS_LABELS: Record<string, string> = {
  retrieve: "Searching knowledge base…",
  web_search: "Searching the web…",
}

// ---------------------------------------------------------------------------
// Streaming chat
// ---------------------------------------------------------------------------

/**
 * Send a message to the backend and yield `StreamEvent` objects as
 * they arrive over the SSE connection.
 *
 * Two event types are yielded:
 * - `{ type: "status", status: "…" }` — agent is thinking / calling a tool
 * - `{ type: "token",  content: "…" }` — a piece of the AI response text
 *
 * @param message  - The user's question / message text.
 * @param options  - Optional retriever, context, and config overrides.
 * @param signal   - An AbortSignal to cancel the stream early.
 */
export async function* streamChatResponse(
  message: string,
  options?: StreamChatOptions,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const apiUrl = `${API_BASE_URL}/api/chat`
  
  let res: Response
  try {
    res = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        thread_id: options?.threadId,
        retriever: options?.retriever,
        context: options?.context,
        config: options?.config,
      }),
      signal,
    })

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unknown error")
      throw new Error(`API error (${res.status}): ${errorText}`)
    }
  } catch (err) {
    // Provide helpful error message for common issues
    if (err instanceof TypeError && err.message.includes("Failed to fetch")) {
      const isLocalhost = API_BASE_URL.includes("localhost")
      const hint = isLocalhost
        ? "Make sure the backend is running: `npm run dev:python` or `uv run uvicorn api.index:app --host 0.0.0.0 --port 8000 --reload`"
        : "Check that NEXT_PUBLIC_API_URL is set correctly for your deployment environment"
      throw new Error(
        `Failed to connect to backend at ${apiUrl}. ${hint}. Original error: ${err.message}`
      )
    }
    throw err
  }

  if (!res.body) {
    throw new Error("Response body is empty — streaming not supported?")
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE events are separated by double newlines
      const events = buffer.split("\n\n")
      buffer = events.pop()! // last element may be incomplete — keep in buffer

      for (const event of events) {
        if (!event.trim()) continue

        // Find the "data: ..." line in the SSE event
        const dataLine = event
          .split("\n")
          .find((line) => line.startsWith("data: "))

        if (!dataLine) continue

        try {
          const payload = JSON.parse(dataLine.slice(6)) // strip "data: "
          const [msg] = payload as [LangChainMessageChunk, unknown]

          const isAI =
            msg.type === "ai" ||
            msg.type === "AIMessageChunk" ||
            msg.type === "AIMessage"

          const isTool =
            msg.type === "tool" || msg.type === "ToolMessage"

          const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0
          const hasToolChunks = msg.tool_call_chunks && msg.tool_call_chunks.length > 0

          // ── AI message requesting a tool call → status event ──
          // Check both `tool_calls` (complete) and `tool_call_chunks`
          // (incremental) because streaming may only populate chunks.
          if (isAI && (hasToolCalls || hasToolChunks)) {
            const toolName =
              (hasToolCalls && msg.tool_calls![0].name) ||
              (hasToolChunks && msg.tool_call_chunks![0].name) ||
              null
            if (toolName) {
              const label =
                TOOL_STATUS_LABELS[toolName] ?? `Calling ${toolName}…`
              yield { type: "status", status: label }
            }
            continue
          }

          // ── Tool response came back → status event ──
          if (isTool) {
            yield { type: "status", status: "Generating response…" }
            continue
          }

          // ── AI content token → token event ──
          if (isAI && msg.content && !hasToolCalls && !hasToolChunks) {
            yield { type: "token", content: msg.content }
          }
        } catch {
          // Malformed event — skip silently
          console.warn("[api] Failed to parse SSE event:", event)
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------

/** Fetch the list of available retriever strategy names. */
export async function fetchRetrievers(): Promise<string[]> {
  const res = await fetch(`${API_BASE_URL}/api/retrievers`)
  if (!res.ok) throw new Error(`Failed to fetch retrievers (${res.status})`)
  const data: { retrievers: string[] } = await res.json()
  return data.retrievers
}

/** Quick health-check — returns true if the backend is reachable. */
export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/`, { signal: AbortSignal.timeout(3000) })
    return res.ok
  } catch {
    return false
  }
}
