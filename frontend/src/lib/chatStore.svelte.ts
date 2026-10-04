import { api, type GeneratedAnswer } from './api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  answer?: GeneratedAnswer
  error?: boolean
}

export interface Chat {
  id: string
  title: string
  updatedAt: number
  messages: ChatMessage[]
}

const KEY = 'knowledge-hub.chats.v1'

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36)

function load(): Chat[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Chat[]) : []
  } catch {
    return []
  }
}

/** App-wide chat state. Lives outside components so an in-flight answer survives navigation. */
class ChatStore {
  chats = $state<Chat[]>(load())
  pending = $state<Record<string, boolean>>({})

  get(id: string | undefined) {
    return this.chats.find((c) => c.id === id)
  }

  private save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.chats))
    } catch {
      /* storage unavailable: chats stay in memory only */
    }
  }

  private upsert(chat: Chat) {
    this.chats = [chat, ...this.chats.filter((c) => c.id !== chat.id)].sort((a, b) => b.updatedAt - a.updatedAt)
    this.save()
  }

  remove(id: string) {
    this.chats = this.chats.filter((c) => c.id !== id)
    this.save()
  }

  /** Sends a question; returns the chat id so the caller can navigate to it when the chat is new. */
  send(question: string, chatId?: string): string {
    const text = question.trim()
    const existing = this.get(chatId)
    const base: Chat = existing ?? { id: uid(), title: text.slice(0, 48), updatedAt: Date.now(), messages: [] }
    if (!text || this.pending[base.id]) return base.id

    const withUser: Chat = {
      ...base,
      updatedAt: Date.now(),
      messages: [...base.messages, { id: uid(), role: 'user', text }],
    }
    this.upsert(withUser)
    this.pending[base.id] = true

    void api
      .ask(text)
      .then(
        (answer): ChatMessage => ({ id: uid(), role: 'assistant', text: answer.summary_answer, answer }),
        (e: unknown): ChatMessage => ({
          id: uid(),
          role: 'assistant',
          text: e instanceof Error ? e.message : 'Something went wrong.',
          error: true,
        }),
      )
      .then((reply) => {
        // Re-read: the chat may have gained messages (or been deleted) while waiting.
        const latest = this.get(base.id)
        if (latest) this.upsert({ ...latest, updatedAt: Date.now(), messages: [...latest.messages, reply] })
        this.pending[base.id] = false
      })

    return base.id
  }
}

export const chatStore = new ChatStore()
