import { useState, useCallback, useRef } from 'react'
import { fetchChat } from '../utils/api'
import type { ChatMessage, SSEEvent } from '../types'

interface UseChatReturn {
  messages: ChatMessage[]
  sendMessage: (sessionId: string, text: string) => Promise<void>
  isStreaming: boolean
  error: string | null
  clearMessages: () => void
}

function randomId(): string {
  return Math.random().toString(36).slice(2)
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (sessionId: string, text: string) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const userMsg: ChatMessage = { id: randomId(), role: 'user', content: text }
    const assistantId = randomId()
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsStreaming(true)
    setError(null)

    try {
      await fetchChat(
        sessionId,
        text,
        (event: SSEEvent) => {
          if (event.type === 'token') {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + event.text }
                  : m,
              ),
            )
          } else if (event.type === 'done') {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId ? { ...m, streaming: false } : m,
              ),
            )
          } else if (event.type === 'error') {
            setError(event.message)
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: `Error: ${event.message}`, streaming: false }
                  : m,
              ),
            )
          }
        },
        controller.signal,
      )
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        const msg = err instanceof Error ? err.message : 'Chat failed'
        setError(msg)
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${msg}`, streaming: false }
              : m,
          ),
        )
      }
    } finally {
      setIsStreaming(false)
    }
  }, [])

  const clearMessages = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setError(null)
    setIsStreaming(false)
  }, [])

  return { messages, sendMessage, isStreaming, error, clearMessages }
}
