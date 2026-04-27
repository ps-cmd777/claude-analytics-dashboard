import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, Zap, Sparkles } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import type { AnalysisResult } from '../types'

interface ChatInterfaceProps { sessionId: string; analysis?: AnalysisResult | null }

function buildSuggestions(analysis?: AnalysisResult | null) {
  if (analysis?.key_findings?.length) {
    return [
      { text: `Which department or segment has the biggest gap vs average?`, tag: 'Insight', tagColor: '#6C47FF', tagBg: 'rgba(108,71,255,0.1)' },
      { text: `What is driving the highest variance in this dataset?`,        tag: 'Insight', tagColor: '#6C47FF', tagBg: 'rgba(108,71,255,0.1)' },
      { text: `Which columns have the most missing data and what should I do?`, tag: 'Quality', tagColor: '#FF6B35', tagBg: 'rgba(255,107,53,0.1)' },
      { text: `What are the top 3 actions I should take based on this data?`, tag: 'Action',  tagColor: '#00C896', tagBg: 'rgba(0,200,150,0.1)' },
    ]
  }
  return [
    { text: 'What are the most important trends in this dataset?',         tag: 'Insight', tagColor: '#6C47FF', tagBg: 'rgba(108,71,255,0.1)' },
    { text: 'Which columns have data quality issues I should fix first?',  tag: 'Quality', tagColor: '#FF6B35', tagBg: 'rgba(255,107,53,0.1)' },
    { text: 'What are the strongest correlations between columns?',        tag: 'Insight', tagColor: '#6C47FF', tagBg: 'rgba(108,71,255,0.1)' },
    { text: 'What would you recommend I do next with this dataset?',       tag: 'Action',  tagColor: '#00C896', tagBg: 'rgba(0,200,150,0.1)' },
  ]
}

const spring = { type: 'spring', stiffness: 90, damping: 18 } as const

export function ChatInterface({ sessionId, analysis }: ChatInterfaceProps) {
  const { messages, sendMessage, isStreaming } = useChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const suggestions = buildSuggestions(analysis)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const submit = async (text: string) => {
    const t = text.trim(); if (!t || isStreaming) return
    setInput(''); await sendMessage(sessionId, t)
  }
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(input) }
  }

  return (
    <div
      className="flex flex-col overflow-hidden rounded-2xl"
      style={{
        height: 520,
        background: '#FFFFFF',
        border: '1px solid #E5E0D8',
        boxShadow: '0 4px 24px rgba(0,0,0,0.05)',
      }}
    >
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-5 py-3.5 flex-shrink-0"
        style={{ borderBottom: '1px solid #F0ECE5', background: '#FAFAF8' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 3px 10px rgba(108,71,255,0.3)' }}
          >
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-[13px] font-[700] text-[#0F0F1A]">Ask about your data</p>
            <p className="text-[11px] text-[#9CA3AF]">Claude has full context of your dataset</p>
          </div>
        </div>
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full"
              style={{ background: 'rgba(108,71,255,0.08)', color: '#6C47FF', border: '1px solid rgba(108,71,255,0.2)' }}
            >
              <Sparkles className="w-3 h-3" />
              Thinking…
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3" style={{ background: '#F9F8F6' }}>
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-5">
            <div className="text-center">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3"
                style={{ background: 'linear-gradient(135deg, rgba(108,71,255,0.12), rgba(108,71,255,0.06))' }}
              >
                <Sparkles className="w-6 h-6" style={{ color: '#6C47FF' }} />
              </div>
              <p className="text-[14px] font-[700] text-[#0F0F1A] mb-1">What would you like to know?</p>
              <p className="text-[12px] text-[#9CA3AF]">Ask anything — Claude knows every column, stat, and pattern</p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full">
              {suggestions.map(s => (
                <button
                  key={s.text}
                  onClick={() => submit(s.text)}
                  className="group text-left flex items-start gap-3 rounded-xl px-4 py-3 transition-all duration-200 hover:shadow-sm"
                  style={{ background: '#FFFFFF', border: '1px solid #E5E0D8' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(108,71,255,0.35)'
                    e.currentTarget.style.background = 'rgba(108,71,255,0.02)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#E5E0D8'
                    e.currentTarget.style.background = '#FFFFFF'
                  }}
                >
                  <span
                    className="flex-shrink-0 text-[9px] font-[800] tracking-widest px-2 py-1 rounded-lg uppercase mt-0.5"
                    style={{ background: s.tagBg, color: s.tagColor }}
                  >
                    {s.tag}
                  </span>
                  <span className="text-[13px] text-[#374151] leading-snug group-hover:text-[#0F0F1A] transition-colors">
                    {s.text}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={spring}
              className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start gap-2.5'}
            >
              {msg.role === 'assistant' && (
                <div
                  className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                  style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 2px 6px rgba(108,71,255,0.3)' }}
                >
                  <Zap className="w-3 h-3 text-white" />
                </div>
              )}
              <div
                className={[
                  'max-w-[84%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed',
                  msg.role === 'user' ? 'rounded-tr-sm text-white' : 'rounded-tl-sm',
                ].join(' ')}
                style={msg.role === 'user'
                  ? { background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 3px 12px rgba(108,71,255,0.25)' }
                  : { background: '#FFFFFF', border: '1px solid #E5E0D8', color: '#374151', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }
                }
              >
                <span className="whitespace-pre-wrap">{msg.content}</span>
                {msg.streaming && msg.content && (
                  <span
                    className="inline-block w-0.5 h-3.5 ml-0.5 rounded-full align-middle animate-pulse"
                    style={{ background: '#6C47FF' }}
                  />
                )}
                {msg.streaming && !msg.content && (
                  <span className="inline-flex gap-1 items-center">
                    {[0, 150, 300].map(d => (
                      <span
                        key={d}
                        className="w-1.5 h-1.5 rounded-full animate-bounce"
                        style={{ background: '#9CA3AF', animationDelay: `${d}ms` }}
                      />
                    ))}
                  </span>
                )}
              </div>
            </motion.div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input ── */}
      <div className="p-4 flex-shrink-0" style={{ borderTop: '1px solid #E5E0D8', background: '#FFFFFF' }}>
        <div className="flex gap-2.5 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about your data…"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl text-[13px] px-4 py-2.5 text-[#0F0F1A] placeholder-[#C4BAF0] focus:outline-none disabled:opacity-50 transition-all"
            style={{
              background: '#F7F4EF',
              border: '1.5px solid #E5E0D8',
              lineHeight: '1.5',
            }}
            onFocus={e => (e.currentTarget.style.borderColor = '#6C47FF')}
            onBlur={e => (e.currentTarget.style.borderColor = '#E5E0D8')}
          />
          <button
            onClick={() => submit(input)}
            disabled={!input.trim() || isStreaming}
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all hover:opacity-90 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:pointer-events-none"
            style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 4px 12px rgba(108,71,255,0.35)' }}
          >
            {isStreaming
              ? <Loader2 className="w-4 h-4 text-white animate-spin" />
              : <Send className="w-4 h-4 text-white" />
            }
          </button>
        </div>
        <p className="text-[10px] text-[#C4BAF0] mt-2 text-center tracking-wide">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
