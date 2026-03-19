/**
 * chat-storage.ts — Persist conversations in localStorage so refresh doesn't clear history.
 */
import type { Conversation, Message } from "@/lib/chat-data"

export const CHAT_STORAGE_KEY = "alpha-guide-chat-state-v1"

export interface PersistedChatState {
  version: 1
  conversations: Conversation[]
  activeConversationId: string | null
}

interface SerializedMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  biblePassages?: Message["biblePassages"]
  alphaThemes?: Message["alphaThemes"]
  feedback?: Message["feedback"]
  saved?: boolean
}

interface SerializedConversation {
  id: string
  title: string
  messages: SerializedMessage[]
  createdAt: string
}

interface SerializedState {
  version: 1
  conversations: SerializedConversation[]
  activeConversationId: string | null
}

function reviveMessage(m: SerializedMessage): Message {
  return { ...m, timestamp: new Date(m.timestamp) }
}

function reviveConversation(c: SerializedConversation): Conversation {
  return {
    id: c.id,
    title: c.title,
    messages: c.messages.map(reviveMessage),
    createdAt: new Date(c.createdAt),
  }
}

export function loadChatStateFromStorage(): PersistedChatState | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as SerializedState
    if (parsed.version !== 1 || !Array.isArray(parsed.conversations)) return null
    return {
      version: 1,
      conversations: parsed.conversations.map(reviveConversation),
      activeConversationId: parsed.activeConversationId ?? null,
    }
  } catch {
    return null
  }
}

export function saveChatStateToStorage(state: PersistedChatState): void {
  if (typeof window === "undefined") return
  try {
    const payload: SerializedState = {
      version: 1,
      conversations: state.conversations.map((c) => ({
        id: c.id,
        title: c.title,
        createdAt: c.createdAt.toISOString(),
        messages: c.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp.toISOString(),
          biblePassages: m.biblePassages,
          alphaThemes: m.alphaThemes,
          feedback: m.feedback,
          saved: m.saved,
        })),
      })),
      activeConversationId: state.activeConversationId,
    }
    window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn("[chat-storage] Failed to save:", e)
  }
}

export function clearChatStorage(): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.removeItem(CHAT_STORAGE_KEY)
  } catch {}
}
