"use client"

import { STARTER_PROMPTS } from "@/lib/chat-data"
import { TrendingUp } from "lucide-react"

interface WelcomeCardProps {
  onPromptClick: (prompt: string) => void
}

export function WelcomeCard({ onPromptClick }: WelcomeCardProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-10">
        <div className="space-y-4 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-lg bg-muted/30 text-foreground/60">
            <TrendingUp className="size-6" />
          </div>
          <h2 className="text-xl font-medium text-foreground tracking-tight">
            AI Financial Assistant
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground max-w-md mx-auto">
            Professional guidance for your financial questions. Ask about markets, investments, or trading strategies.
          </p>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onPromptClick(prompt)}
              className="rounded-lg border border-border/50 bg-background p-3.5 text-left text-sm text-foreground/80 transition-all hover:bg-muted/30 hover:border-border"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
