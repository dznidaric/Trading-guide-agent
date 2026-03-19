"use client"

import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-data"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Copy,
  Bookmark,
  BookmarkCheck,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react"

interface ChatMessageProps {
  message: Message
  showBiblePassages: boolean
  onFeedback: (messageId: string, feedback: "up" | "down") => void
  onSave: (messageId: string) => void
  onCopy: (content: string) => void
}

export function ChatMessage({
  message,
  showBiblePassages,
  onFeedback,
  onSave,
  onCopy,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === "user"

  const handleCopy = () => {
    onCopy(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className={cn(
        "flex w-full group",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "flex flex-col",
          isUser ? "items-end max-w-[75%]" : "items-start max-w-full"
        )}
      >
        <div
          className={cn(
            "text-sm leading-relaxed",
            isUser
              ? "rounded-2xl rounded-br-sm px-4 py-2.5 bg-muted/60 text-foreground"
              : "px-0 py-1 text-foreground/90"
          )}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {!isUser && (
          <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-muted-foreground hover:text-foreground"
              onClick={() => onSave(message.id)}
              aria-label={message.saved ? "Unsave message" : "Save message"}
            >
              {message.saved ? (
                <BookmarkCheck className="size-3.5 text-primary" />
              ) : (
                <Bookmark className="size-3.5" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
              aria-label="Copy message"
            >
              <Copy className="size-3.5" />
              {copied && <span className="text-xs ml-1">Copied</span>}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 px-2",
                message.feedback === "up"
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onFeedback(message.id, "up")}
              aria-label="Thumbs up"
            >
              <ThumbsUp className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 px-2",
                message.feedback === "down"
                  ? "text-destructive"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onFeedback(message.id, "down")}
              aria-label="Thumbs down"
            >
              <ThumbsDown className="size-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
