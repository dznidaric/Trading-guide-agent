"use client"

import { TOPIC_GUIDES } from "@/lib/chat-data"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  TrendingUp,
  BarChart,
  PieChart,
  Shield,
  LineChart,
} from "lucide-react"
import type { ReactNode } from "react"

const iconMap: Record<string, ReactNode> = {
  "trending-up": <TrendingUp className="size-5" />,
  "bar-chart": <BarChart className="size-5" />,
  "pie-chart": <PieChart className="size-5" />,
  shield: <Shield className="size-5" />,
  "line-chart": <LineChart className="size-5" />,
}

interface TopicGuidesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onStartChat: (topic: string) => void
}

export function TopicGuidesDialog({
  open,
  onOpenChange,
  onStartChat,
}: TopicGuidesDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-medium">Topic Guides</DialogTitle>
          <DialogDescription>
            Explore key financial topics. Pick a topic to start a conversation about investing and markets.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2 mt-2">
          {TOPIC_GUIDES.map((topic) => (
            <div
              key={topic.id}
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:bg-secondary/50"
            >
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  {iconMap[topic.icon]}
                </div>
                <h3 className="text-sm font-semibold text-foreground">
                  {topic.title}
                </h3>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {topic.description}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="self-start mt-auto text-xs"
                onClick={() => {
                  onStartChat(topic.title)
                  onOpenChange(false)
                }}
              >
                Start chat about this
              </Button>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
