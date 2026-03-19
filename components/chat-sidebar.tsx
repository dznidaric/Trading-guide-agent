"use client"

import { cn } from "@/lib/utils"
import type { Conversation } from "@/lib/chat-data"
import { TOPIC_CHIPS } from "@/lib/chat-data"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Plus, MessageSquare, X } from "lucide-react"

interface ChatSidebarProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  onTopicChipClick: (topic: string) => void
  isOpen: boolean
  onClose: () => void
}

export function ChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onTopicChipClick,
  isOpen,
  onClose,
}: ChatSidebarProps) {
  const todayConvos = conversations.filter(
    (c) => c.createdAt.toDateString() === new Date().toDateString()
  )
  const olderConvos = conversations.filter(
    (c) => c.createdAt.toDateString() !== new Date().toDateString()
  )

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-300 md:relative md:z-0 md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between p-4">
          <Button
            onClick={onNewChat}
            className="flex-1 gap-2 rounded-xl"
            size="sm"
          >
            <Plus className="size-4" />
            New chat
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="ml-2 md:hidden h-8 w-8 p-0"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X className="size-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1 px-3">
          {/* Topic chips */}
          <div className="pb-3">
            <p className="px-2 pb-2 text-xs font-medium text-sidebar-foreground/60 uppercase tracking-wider">
              Topics
            </p>
            <div className="flex flex-wrap gap-1.5">
              {TOPIC_CHIPS.map((topic) => (
                <button
                  key={topic}
                  onClick={() => onTopicChipClick(topic)}
                  className="rounded-full border border-sidebar-border bg-sidebar px-2.5 py-1 text-xs text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>

          <Separator className="mb-3" />

          {/* Conversations */}
          {todayConvos.length > 0 && (
            <div className="pb-3">
              <p className="px-2 pb-2 text-xs font-medium text-sidebar-foreground/60 uppercase tracking-wider">
                Today
              </p>
              <div className="flex flex-col gap-0.5">
                {todayConvos.map((convo) => (
                  <button
                    key={convo.id}
                    onClick={() => onSelectConversation(convo.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                      activeConversationId === convo.id
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50"
                    )}
                  >
                    <MessageSquare className="size-4 shrink-0" />
                    <span className="truncate">{convo.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {olderConvos.length > 0 && (
            <div className="pb-3">
              <p className="px-2 pb-2 text-xs font-medium text-sidebar-foreground/60 uppercase tracking-wider">
                Previous
              </p>
              <div className="flex flex-col gap-0.5">
                {olderConvos.map((convo) => (
                  <button
                    key={convo.id}
                    onClick={() => onSelectConversation(convo.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                      activeConversationId === convo.id
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50"
                    )}
                  >
                    <MessageSquare className="size-4 shrink-0" />
                    <span className="truncate">{convo.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </ScrollArea>

        <div className="border-t border-sidebar-border p-3">
          <p className="text-xs text-center text-sidebar-foreground/50 leading-relaxed">
            Financial guidance for informational and trading purposes.
          </p>
        </div>
      </aside>
    </>
  )
}
