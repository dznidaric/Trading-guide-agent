"use client"

import { Loader2 } from "lucide-react"

interface TypingIndicatorProps {
  /** When provided, displays a short status label (e.g. "Searching knowledge base…").
   *  When absent/null, falls back to the generic bouncing-dots animation. */
  status?: string | null
}

/**
 * Visual indicator shown while the agent is processing a request.
 *
 * Two modes:
 * 1. **Status mode** — a spinner + descriptive label (tool calling, fetching, etc.)
 * 2. **Dots mode** — three bouncing dots (generic "typing…" feel)
 */
export function TypingIndicator({ status }: TypingIndicatorProps) {
  return (
    <div className="flex items-start">
      <div className="px-0 py-1">
        {status ? (
          /* Status mode — spinner + label */
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            <span>{status}</span>
          </div>
        ) : (
          /* Dots mode — generic typing animation */
          <div className="flex items-center gap-1.5">
            <div className="size-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
            <div className="size-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
            <div className="size-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
          </div>
        )}
      </div>
    </div>
  )
}
