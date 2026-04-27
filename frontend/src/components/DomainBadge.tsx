import { useState, useRef, useEffect } from 'react'
import { Pencil, X, Check, Loader2 } from 'lucide-react'

interface DomainBadgeProps {
  domain: string
  grain: string
  onCorrect: (correctedDomain: string) => void
  isRerunning?: boolean
}

export function DomainBadge({ domain, grain, onCorrect, isRerunning }: DomainBadgeProps) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) {
      setValue(domain)
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing, domain])

  function submit() {
    const trimmed = value.trim()
    if (trimmed && trimmed !== domain) {
      onCorrect(trimmed)
    }
    setEditing(false)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter') submit()
    if (e.key === 'Escape') setEditing(false)
  }

  const grainLabel = grain
    .replace('one row = ', '')
    .replace('one row per ', '')

  if (isRerunning) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 32px', borderBottom: '1px solid #E8E8F0',
        background: 'rgba(108,71,255,0.03)',
      }}>
        <Loader2 style={{ width: 13, height: 13, color: '#6C47FF', animation: 'spin 1s linear infinite' }} />
        <span style={{ fontSize: 12, color: '#6C47FF', fontWeight: 500 }}>
          Re-running analysis with corrected domain…
        </span>
      </div>
    )
  }

  if (!domain) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      padding: '8px 32px', borderBottom: '1px solid #E8E8F0',
      background: 'rgba(108,71,255,0.025)',
    }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: '#9CA3AF', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        Detected
      </span>

      {editing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            ref={inputRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKey}
            placeholder="e.g. Hospital patient records"
            style={{
              fontSize: 12, fontWeight: 500, color: '#0F0F1A',
              background: '#fff', border: '1.5px solid #6C47FF',
              borderRadius: 8, padding: '4px 10px', outline: 'none',
              width: 260, fontFamily: 'inherit',
              boxShadow: '0 0 0 3px rgba(108,71,255,0.12)',
            }}
          />
          <button onClick={submit} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 26, height: 26, borderRadius: 6, border: 'none', cursor: 'pointer',
            background: '#6C47FF', color: '#fff',
          }}>
            <Check style={{ width: 12, height: 12 }} />
          </button>
          <button onClick={() => setEditing(false)} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 26, height: 26, borderRadius: 6, border: '1px solid #E8E8F0',
            cursor: 'pointer', background: '#fff', color: '#6B7280',
          }}>
            <X style={{ width: 12, height: 12 }} />
          </button>
        </div>
      ) : (
        <>
          <span style={{
            fontSize: 12, fontWeight: 600, color: '#6C47FF',
            padding: '3px 10px', borderRadius: 999,
            background: 'rgba(108,71,255,0.08)',
            border: '1px solid rgba(108,71,255,0.18)',
          }}>
            {domain}
          </span>

          {grainLabel && (
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>
              · {grainLabel}
            </span>
          )}

          <button
            onClick={() => setEditing(true)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              fontSize: 11, fontWeight: 500, color: '#9CA3AF',
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'inherit', padding: '2px 6px', borderRadius: 6,
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#6C47FF')}
            onMouseLeave={e => (e.currentTarget.style.color = '#9CA3AF')}
          >
            <Pencil style={{ width: 10, height: 10 }} />
            Not quite right?
          </button>
        </>
      )}
    </div>
  )
}
