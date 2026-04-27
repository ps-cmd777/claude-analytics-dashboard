import { useState, useCallback, useRef, useEffect } from 'react'
import { X, SlidersHorizontal } from 'lucide-react'
import type { DataProfile } from '../types'

interface FilterBarProps {
  originalProfile: DataProfile
  filters: Record<string, string>
  onFiltersChange: (filters: Record<string, string>) => void
  loading?: boolean
}

function FilterChip({
  col, value, options, isActive, loading,
  onChange, onClear,
}: {
  col: string; value: string; options: string[]; isActive: boolean;
  onChange: (v: string) => void; onClear: () => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const label = col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 10px 6px 12px', borderRadius: 999, cursor: 'pointer',
          fontSize: 13, fontWeight: isActive ? 600 : 400, fontFamily: 'inherit',
          background: isActive ? 'rgba(108,71,255,0.08)' : '#fff',
          border: `1.5px solid ${isActive ? 'rgba(108,71,255,0.35)' : '#E8E8F0'}`,
          color: isActive ? '#6C47FF' : '#3F3F5A',
          transition: 'all 0.15s ease',
          boxShadow: '0 1px 2px rgba(15,15,26,0.04)',
        }}>
        {isActive && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#6C47FF', flexShrink: 0 }} />}
        <span style={{ color: isActive ? '#6C47FF' : '#8B8BA7', fontWeight: 500 }}>{label}:</span>
        <span>{isActive ? value : 'All'}</span>
        {isActive ? (
          <span
            onClick={e => { e.stopPropagation(); onClear() }}
            style={{ display: 'flex', alignItems: 'center', marginLeft: 2, opacity: 0.7, cursor: 'pointer' }}>
            <X style={{ width: 12, height: 12 }} />
          </span>
        ) : (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', left: 0, zIndex: 50,
          background: '#fff', borderRadius: 12, border: '1px solid #E8E8F0', minWidth: 160,
          boxShadow: '0 8px 24px -4px rgba(15,15,26,0.12), 0 2px 6px -2px rgba(15,15,26,0.06)',
          overflow: 'hidden',
        }}>
          <button
            onClick={() => { onChange(''); setOpen(false) }}
            style={{
              display: 'block', width: '100%', padding: '9px 14px', textAlign: 'left',
              fontSize: 13, fontFamily: 'inherit', cursor: 'pointer', border: 'none',
              background: !isActive ? 'rgba(108,71,255,0.06)' : 'transparent',
              color: !isActive ? '#6C47FF' : '#3F3F5A', fontWeight: !isActive ? 600 : 400,
            }}>
            All
          </button>
          {options.map(opt => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false) }}
              style={{
                display: 'block', width: '100%', padding: '9px 14px', textAlign: 'left',
                fontSize: 13, fontFamily: 'inherit', cursor: 'pointer', border: 'none',
                background: value === opt ? 'rgba(108,71,255,0.06)' : 'transparent',
                color: value === opt ? '#6C47FF' : '#3F3F5A', fontWeight: value === opt ? 600 : 400,
              }}>
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function FilterBar({ originalProfile, filters, onFiltersChange, loading }: FilterBarProps) {
  const filterColumns = originalProfile.categorical_columns
    .filter(col => {
      const cp = originalProfile.column_profiles[col]
      return cp && cp.unique_count >= 2 && cp.unique_count <= 30
    })
    .slice(0, 8)

  const setFilter = useCallback((col: string, value: string) => {
    if (value === '') {
      const next = { ...filters }; delete next[col]; onFiltersChange(next)
    } else {
      onFiltersChange({ ...filters, [col]: value })
    }
  }, [filters, onFiltersChange])

  const activeCount = Object.keys(filters).length

  if (filterColumns.length === 0) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      padding: '10px 32px', borderBottom: '1px solid #E8E8F0', background: '#fff',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 4, flexShrink: 0 }}>
        <SlidersHorizontal style={{ width: 13, height: 13, color: '#8B8BA7' }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#8B8BA7', letterSpacing: '0.01em' }}>Filters</span>
      </div>

      {filterColumns.map(col => {
        const cp = originalProfile.column_profiles[col]
        const options = Object.keys(cp.top_values)
        return (
          <FilterChip
            key={col} col={col} value={filters[col] ?? ''} options={options}
            isActive={!!filters[col]}
            onChange={v => setFilter(col, v)}
            onClear={() => setFilter(col, '')}
          />
        )
      })}

      {loading && (
        <span style={{ fontSize: 12, color: '#6C47FF', fontWeight: 500, marginLeft: 4, opacity: 0.8 }}>
          Filtering…
        </span>
      )}

      {activeCount > 0 && (
        <button
          onClick={() => onFiltersChange({})}
          style={{
            marginLeft: 'auto', fontSize: 12, fontWeight: 500, color: '#EF4444',
            background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
          <X style={{ width: 12, height: 12 }} /> Clear all
        </button>
      )}
    </div>
  )
}
