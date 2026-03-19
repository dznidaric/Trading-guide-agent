"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { SendHorizontal } from "lucide-react"

interface ChatComposerProps {
  onSend: (message: string) => void
  disabled?: boolean
  suggestedPrompts?: string[]
  onSuggestedPromptClick?: (prompt: string) => void
}

export function ChatComposer({
  onSend,
  disabled = false,
  suggestedPrompts,
  onSuggestedPromptClick,
}: ChatComposerProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-3">
      {suggestedPrompts && suggestedPrompts.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onSuggestedPromptClick?.(prompt)}
              className="rounded-md border border-border/50 bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 rounded-lg border border-border/50 bg-background px-3 py-2.5">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about markets, investments, or financial guidance..."
          className="min-h-[44px] max-h-[160px] flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none"
          rows={1}
          disabled={disabled}
          aria-label="Type your message"
        />
        <Button
          size="sm"
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="shrink-0 rounded-md h-9 w-9 p-0"
          aria-label="Send message"
        >
          <SendHorizontal className="size-4" />
        </Button>
      </div>
    </div>
  )
}
