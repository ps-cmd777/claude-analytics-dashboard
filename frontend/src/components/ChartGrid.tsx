import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { DataProfile } from '../types'

interface ChartGridProps { profile: DataProfile; skipDistributions?: Set<string> }

const VIOLET_RAMP = ['#6C47FF', '#4F35CC', '#8666FF', '#3A28B8', '#5A3DE0', '#7855FF', '#4228CC', '#9077FF']
const CATEGORICAL_PALETTE = ['#6C47FF', '#FF6B35', '#00C896', '#FFB800', '#E04875', '#4F35CC', '#FF8A3D', '#00A87D']

const TIP_STYLE = {
  fontSize: 12, borderRadius: 8,
  background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.08)', color: '#EEF2FF',
}

const ABBREV: Record<string, string> = {
  emp: 'Employee', dept: 'Department', mgr: 'Manager', yrs: 'Years',
  yr: 'Year', pct: 'Percentage', id: 'ID', num: 'Number', avg: 'Average',
  perf: 'Performance', sat: 'Satisfaction', eng: 'Engagement',
  rev: 'Revenue', amt: 'Amount', qty: 'Quantity', cnt: 'Count',
  loc: 'Location', pos: 'Position', lvl: 'Level', grp: 'Group',
  usd: 'USD', sal: 'Salary', comp: 'Compensation', inc: 'Income',
  exp: 'Experience', promo: 'Promotion', edu: 'Education',
}

function formatColName(col: string): string {
  return col.replace(/_/g, ' ').split(' ').map(word => {
    const lower = word.toLowerCase()
    return ABBREV[lower] ?? (word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
  }).join(' ')
}

function isIdColumn(col: string): boolean {
  const lower = col.toLowerCase()
  return ['_id', 'id_', 'employee_id', 'worker_id', 'emp_id', 'user_id', 'person_id']
    .some(p => lower.includes(p)) || lower === 'id'
}

function fmt(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}k`
  return v.toFixed(v % 1 === 0 ? 0 : 1)
}

// ── Generate approximate histogram bars from 5-number summary ────────────
function approxBars(min: number, q25: number, median: number, q75: number, max: number): number[] {
  // Creates a 10-bar normal-ish distribution weighted by the quartile positions
  const range = max - min || 1
  const center = (median - min) / range
  const spread = (q75 - q25) / range
  return Array.from({ length: 10 }, (_, i) => {
    const x = (i + 0.5) / 10
    const dist = Math.abs(x - center)
    const h = Math.max(6, Math.round(100 * Math.exp(-(dist * dist) / (2 * (spread || 0.12) * (spread || 0.12)))))
    return Math.min(100, h)
  })
}

// ── Compact numeric distribution card (matches design's MiniDist) ─────────
function DistributionCard({ colName, profile }: { colName: string; profile: DataProfile }) {
  const cp = profile.column_profiles[colName]
  if (!cp || cp.mean === null) return null
  if (cp.missing_pct > 50) return null
  const { min_val, q25, median, q75, max_val, mean, std, missing_pct, dtype } = cp
  if (min_val === null || q25 === null || median === null || q75 === null || max_val === null) return null

  const bars = approxBars(min_val, q25, median, q75, max_val)
  const peakIdx = bars.indexOf(Math.max(...bars))
  const [hoveredBar, setHoveredBar] = useState<number | null>(null)

  const humanName = formatColName(colName)
  const missingDisplay = missing_pct === 0 ? 'None'
    : missing_pct < 0.01 ? '<0.01%' : `${missing_pct.toFixed(1)}%`
  const step = (max_val - min_val) / bars.length

  return (
    <div style={{
      background: '#fff', borderRadius: 14, border: '1px solid #EAECF0',
      padding: '16px 16px 14px',
      boxShadow: '0 1px 3px rgba(15,15,26,0.04), 0 4px 16px -6px rgba(15,15,26,0.08)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#0F0F1A', letterSpacing: '-0.01em' }}>
          {humanName}
        </span>
        <span style={{
          fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
          color: '#6C47FF', padding: '2px 8px', background: 'rgba(108,71,255,0.07)',
          border: '1px solid rgba(108,71,255,0.15)', borderRadius: 4,
        }}>Numeric</span>
      </div>

      {/* Mean — big, prominent */}
      <div style={{ fontSize: 22, fontWeight: 800, color: '#0F0F1A', letterSpacing: '-0.03em',
        fontVariantNumeric: 'tabular-nums', marginBottom: 8 }}>
        {fmt(mean!)}
        <span style={{ fontSize: 11, fontWeight: 500, color: '#9CA3AF', marginLeft: 4 }}>avg</span>
      </div>

      {/* Mini histogram bars with hover tooltip */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: 2, height: 40, marginBottom: 10 }}>
        {bars.map((h, i) => (
          <div
            key={i}
            onMouseEnter={() => setHoveredBar(i)}
            onMouseLeave={() => setHoveredBar(null)}
            style={{
              flex: 1, height: `${h}%`, borderRadius: 3, minHeight: 3, cursor: 'default',
              background: hoveredBar === i
                ? '#4F35CC'
                : i === peakIdx
                  ? 'linear-gradient(180deg, #8666FF 0%, #6C47FF 100%)'
                  : 'rgba(108,71,255,0.22)',
              transition: 'background 0.1s',
            }}
          />
        ))}
        {hoveredBar !== null && (
          <div style={{
            position: 'absolute', bottom: '110%',
            left: `${Math.min(80, (hoveredBar / bars.length) * 100)}%`,
            transform: 'translateX(-30%)',
            background: '#0F0F1A', color: '#EEF2FF',
            fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap',
            padding: '4px 9px', borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.08)',
            pointerEvents: 'none', zIndex: 10,
          }}>
            {fmt(min_val + hoveredBar * step)} – {fmt(min_val + (hoveredBar + 1) * step)}
          </div>
        )}
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4,
        paddingTop: 10, borderTop: '1px solid #F1F1F7' }}>
        {[
          { label: 'Min', value: fmt(min_val), warn: false },
          { label: 'Max', value: fmt(max_val), warn: false },
          { label: 'Missing', value: missingDisplay, warn: missing_pct > 5 },
        ].map(s => (
          <div key={s.label}>
            <div style={{ fontSize: 9, color: '#9CA3AF', textTransform: 'uppercase',
              letterSpacing: '0.07em', fontWeight: 700, marginBottom: 2 }}>
              {s.label}
            </div>
            <div style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums',
              fontWeight: 600, color: s.warn ? '#EF4444' : '#374151' }}>
              {s.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Category breakdown card ────────────────────────────────────────────────
function CategoryCard({ colName, profile, skipCols }: { colName: string; profile: DataProfile; skipCols: Set<string> }) {
  if (isIdColumn(colName) || skipCols.has(colName)) return null
  const cp = profile.column_profiles[colName]
  if (!cp || Object.keys(cp.top_values).length === 0) return null
  if (cp.unique_count > 20 || cp.unique_count <= 2 || cp.missing_pct > 50) return null

  const entries = Object.entries(cp.top_values).slice(0, 8)
  const max = Math.max(...entries.map(([, v]) => v))
  const total = entries.reduce((s, [, v]) => s + v, 0)
  const humanName = formatColName(colName)

  return (
    <div style={{
      background: '#fff', borderRadius: 14, border: '1px solid #E8E8F0',
      padding: '14px 16px',
      boxShadow: '0 1px 3px rgba(15,15,26,0.04), 0 4px 16px -6px rgba(15,15,26,0.08)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#1A1A2E', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '-0.01em' }}>{humanName}</span>
        <span style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
          padding: '3px 6px', borderRadius: 4, background: 'rgba(255,107,53,0.10)', color: '#C0501C' }}>
          CATEGORICAL
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {entries.map(([name, val], i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 90, flexShrink: 0, textAlign: 'right',
              fontSize: 10.5, fontWeight: 500, color: '#374151',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {name}
            </div>
            <div style={{ flex: 1, height: 12, background: 'rgba(108,71,255,0.05)', borderRadius: 3 }}>
              <div style={{
                height: '100%', width: `${(val / max) * 100}%`,
                background: VIOLET_RAMP[i % VIOLET_RAMP.length], borderRadius: 3,
              }} />
            </div>
            <div style={{ width: 34, flexShrink: 0, fontSize: 10, fontWeight: 500,
              color: '#6B7280', fontFamily: 'IBM Plex Mono, monospace',
              fontVariantNumeric: 'tabular-nums' }}>
              {total > 0 ? `${((val / total) * 100).toFixed(0)}%` : ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Correlation heatmap ────────────────────────────────────────────────────
function CorrelationHeatmap({ profile }: { profile: DataProfile }) {
  const cols = profile.numeric_columns.filter(c => !isIdColumn(c))
  if (cols.length < 2) return null

  function cellStyle(r: number, isDiag: boolean) {
    if (isDiag) return { background: '#F4F5F9', color: '#8B8BA7' }
    const abs = Math.abs(r); const pos = r >= 0
    if (abs >= 0.7) return { background: pos ? '#6C47FF' : '#EF4444', color: '#fff', fontWeight: 700 }
    if (abs >= 0.5) return { background: pos ? 'rgba(108,71,255,0.55)' : 'rgba(239,68,68,0.55)', color: '#EEF2FF' }
    if (abs >= 0.3) return { background: pos ? 'rgba(108,71,255,0.25)' : 'rgba(239,68,68,0.25)', color: '#3F3F5A' }
    return { background: '#F4F5F9', color: '#8B8BA7' }
  }

  let maxR = 0; let maxPair = { a: '', b: '', r: 0 }
  for (const a of cols) for (const b of cols) {
    if (a !== b) {
      const r = profile.correlation_matrix[a]?.[b] ?? 0
      if (Math.abs(r) > maxR) { maxR = Math.abs(r); maxPair = { a, b, r } }
    }
  }

  const cellSize = Math.max(44, Math.min(64, Math.floor(520 / cols.length)))

  return (
    <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8E8F0', padding: '20px 24px', boxShadow: '0 1px 2px rgba(15,15,26,0.02), 0 4px 12px -6px rgba(15,15,26,0.06)' }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1A1A2E', marginBottom: 4, letterSpacing: '-0.01em' }}>How Columns Relate to Each Other</h3>
      <p style={{ fontSize: 12, color: '#8B8BA7', marginBottom: 16, lineHeight: 1.5 }}>
        <strong style={{ color: '#6C47FF' }}>Blue</strong> = both rise together · <strong style={{ color: '#EF4444' }}>Red</strong> = one rises as the other falls · stronger color = stronger link
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr>
              <th style={{ width: 140, minWidth: 140 }} />
              {cols.map(c => (
                <th key={c} style={{ width: cellSize, minWidth: cellSize, padding: '4px 2px', textAlign: 'center' }}>
                  <div style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 100, fontSize: 10, color: '#8B8BA7', fontWeight: 500 }}>
                    {formatColName(c)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cols.map(rowCol => (
              <tr key={rowCol}>
                <td style={{ fontSize: 10, color: '#8B8BA7', paddingRight: 12, textAlign: 'right', width: 140, minWidth: 140, fontWeight: 500 }}>
                  {formatColName(rowCol)}
                </td>
                {cols.map(colCol => {
                  const r = profile.correlation_matrix[rowCol]?.[colCol] ?? 0
                  const isDiag = rowCol === colCol
                  const s = cellStyle(r, isDiag)
                  return (
                    <td key={colCol} style={{ ...s, padding: `6px 4px`, fontSize: 11, textAlign: 'center', borderRadius: 4 }}
                      title={isDiag ? 'Same column' : `${formatColName(rowCol)} × ${formatColName(colCol)}: ${r.toFixed(3)}`}>
                      {isDiag ? '—' : r.toFixed(2)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {maxR >= 0.4 && (
        <div style={{ marginTop: 14, padding: '10px 12px', borderRadius: 10, background: 'rgba(108,71,255,0.06)', border: '1px solid rgba(108,71,255,0.15)', fontSize: 12, color: '#3F3F5A', lineHeight: 1.5 }}>
          Strongest link: <strong style={{ color: '#6C47FF' }}>{formatColName(maxPair.a)}</strong> and <strong style={{ color: '#6C47FF' }}>{formatColName(maxPair.b)}</strong> ({maxPair.r.toFixed(2)}).
          {maxR >= 0.7 ? ' Strong signal worth acting on.' : ' Worth monitoring.'}
        </div>
      )}
    </div>
  )
}

// ── Missing data chart ─────────────────────────────────────────────────────
function MissingValuesChart({ profile }: { profile: DataProfile }) {
  const colsWithMissing = Object.values(profile.column_profiles)
    .filter(cp => cp.missing_pct > 0)
    .sort((a, b) => b.missing_pct - a.missing_pct)

  if (colsWithMissing.length === 0) return (
    <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8E8F0', padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(0,200,150,0.1)', display: 'grid', placeItems: 'center', fontSize: 16 }}>✓</div>
      <div>
        <p style={{ fontSize: 14, fontWeight: 600, color: '#00C896', margin: 0 }}>No Missing Values</p>
        <p style={{ fontSize: 12, color: '#8B8BA7', margin: '2px 0 0' }}>Every cell in every column has a value — this dataset is complete.</p>
      </div>
    </div>
  )

  const data = colsWithMissing.map(cp => ({ label: formatColName(cp.name), value: parseFloat(cp.missing_pct.toFixed(1)), count: cp.missing_count }))

  return (
    <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8E8F0', padding: '20px 24px', boxShadow: '0 1px 2px rgba(15,15,26,0.02), 0 4px 12px -6px rgba(15,15,26,0.06)' }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1A1A2E', marginBottom: 4, letterSpacing: '-0.01em' }}>Missing Data by Column</h3>
      <p style={{ fontSize: 12, color: '#8B8BA7', marginBottom: 16 }}>
        {colsWithMissing.length} of {profile.shape[1]} columns have gaps · dashed line = 20% threshold
      </p>
      <ResponsiveContainer width="100%" height={Math.max(80, colsWithMissing.length * 32)}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 50, left: 8, bottom: 0 }}>
          <XAxis type="number" unit="%" tick={{ fontSize: 10, fill: '#8B8BA7' }} domain={[0, 100]} />
          <YAxis type="category" dataKey="label" tick={{ fontSize: 10, fill: '#8B8BA7' }} width={160} />
          <Tooltip formatter={(v: number, _n, p) => [`${v}% missing (${p.payload.count?.toLocaleString() ?? '?'} blank cells)`, p.payload.label]} contentStyle={TIP_STYLE} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.value > 20 ? '#F59E0B' : d.value > 10 ? '#FF6B35' : '#6C47FF'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────
function SectionLabel({ title, description, accent = '#6C47FF' }: { title: string; description: string; accent?: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14,
      padding: '14px 18px', borderRadius: 14, marginBottom: 16,
      background: `linear-gradient(135deg, ${accent}12 0%, ${accent}03 100%)`,
      border: `1px solid ${accent}26`,
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 9, flexShrink: 0,
        background: `${accent}1a`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={accent} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
        </svg>
      </div>
      <div>
        <h2 style={{ fontSize: 16, fontWeight: 800, color: '#1A1A2E', margin: 0, letterSpacing: '-0.015em', lineHeight: 1.1 }}>{title}</h2>
        <p style={{ fontSize: 12, color: '#8B8BA7', margin: '3px 0 0', lineHeight: 1.5 }}>{description}</p>
      </div>
    </div>
  )
}

// ── Main ChartGrid ─────────────────────────────────────────────────────────
export function ChartGrid({ profile, skipDistributions = new Set() }: ChartGridProps) {
  const numericCols = profile.numeric_columns.filter(c => !isIdColumn(c) && !skipDistributions.has(c))
  const categoricalCols = profile.categorical_columns.filter(c => !isIdColumn(c))
  const hasCorrelation = numericCols.length >= 2

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>

      {/* Numeric distributions — 4-column compact grid */}
      {numericCols.length > 0 && (
        <section>
          <SectionLabel
            title="Value Distributions"
            description="How each numeric column is spread across all records — typical values, extremes, and whether the data is balanced or skewed."
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {numericCols.map(col => (
              <DistributionCard key={col} colName={col} profile={profile} />
            ))}
          </div>
        </section>
      )}

      {/* Category breakdowns */}
      {categoricalCols.length > 0 && (
        <section>
          <SectionLabel
            title="Category Breakdown"
            description="Most frequent values in each text column — dominant groups, segments, and team composition."
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
            {categoricalCols.map(col => (
              <CategoryCard key={col} colName={col} profile={profile} skipCols={new Set()} />
            ))}
          </div>
        </section>
      )}

      {/* Relationships + Missing */}
      <section>
        <SectionLabel
          title="Relationships Between Columns"
          description="Which columns move together — essential for understanding what drives outcomes like attrition, revenue, or performance."
          accent="#FF6B35"
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {hasCorrelation && <CorrelationHeatmap profile={profile} />}
          <MissingValuesChart profile={profile} />
        </div>
      </section>

    </div>
  )
}
