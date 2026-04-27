import { useEffect, useState } from 'react'
import {
  BarChart, Bar,
  AreaChart, Area,
  PieChart, Pie, Legend,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { Sparkles } from 'lucide-react'
import { fetchAggregate } from '../utils/api'
import type { ChartSpec } from '../types'

interface DynamicChartGridProps {
  chartSpecs: ChartSpec[]
  sessionId: string
}

type Row = { label: string; value: number }

// KPI card accent colours (one per index 0-3, cycles)
const KPI_ACCENTS = ['#6C47FF', '#FF6B35', '#00C896', '#E04875']

// Categorical palette — different colors per bar/slice to break monotony
const BAR_PALETTE = [
  '#6C47FF', '#FF6B35', '#00C896', '#FFB800',
  '#E04875', '#4F35CC', '#FF8A3D', '#00A87D',
]

const TIP_STYLE = {
  fontSize: 12,
  borderRadius: 8,
  background: '#131B33',
  border: '1px solid rgba(255,255,255,0.08)',
  color: '#EEF2FF',
}

const ABBREV: Record<string, string> = {
  emp: 'Employee', dept: 'Department', mgr: 'Manager', yrs: 'Years',
  yr: 'Year', pct: 'Percentage', id: 'ID', num: 'Number', avg: 'Average',
  rev: 'Revenue', amt: 'Amount', qty: 'Quantity', cnt: 'Count',
  usd: 'USD', sal: 'Salary', comp: 'Compensation', perf: 'Performance',
  sat: 'Satisfaction', loc: 'Location', pos: 'Position', lvl: 'Level',
  grp: 'Group', inc: 'Income', exp: 'Experience', promo: 'Promotion',
}

function formatColName(col: string): string {
  return col
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => {
      const lower = word.toLowerCase()
      return ABBREV[lower] ?? (word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    })
    .join(' ')
}

function fmtVal(val: number, fmt: string = 'number', agg?: string): string {
  if (agg === 'count' || fmt === 'integer') return val.toFixed(0)
  if (fmt === 'currency') {
    return val >= 1_000_000 ? `$${(val / 1_000_000).toFixed(1)}M`
      : val >= 1_000 ? `$${(val / 1_000).toFixed(0)}k`
      : `$${val.toFixed(0)}`
  }
  if (fmt === 'percent') return `${val.toFixed(1)}%`
  return val >= 1_000 ? `${(val / 1_000).toFixed(1)}k` : val.toFixed(1)
}

// ---------------------------------------------------------------------------
// Sparkline SVG (inline, no recharts dependency)
// ---------------------------------------------------------------------------
function Sparkline({ value, accent, index }: { value: number; accent: string; index: number }) {
  // Generate a synthetic 12-point trend line ending at `value`
  const pts = Array.from({ length: 12 }, (_, i) => {
    const progress = i / 11
    const wave = Math.sin(i * 2.1 + index) * 0.08 + Math.cos(i * 1.4 + index * 0.7) * 0.06
    return value * (0.68 + progress * 0.32 + wave)
  })
  pts[11] = value

  const W = 100, H = 36
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const range = max - min || 1
  const points = pts.map((d, i) => ({
    x: (i / (pts.length - 1)) * W,
    y: H - ((d - min) / range) * (H - 6) - 3,
  }))
  const linePath = 'M ' + points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' L ')
  const areaPath = linePath + ` L ${W},${H} L 0,${H} Z`
  const last = points[points.length - 1]
  const gradId = `spark-grad-${index}`

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
      style={{ width: '100%', height: 40, marginTop: 10, display: 'block' }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={accent} stopOpacity="0.22" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} stroke={accent} strokeWidth="1.75" fill="none"
        strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last.x} cy={last.y} r="2.5" fill={accent} />
      <circle cx={last.x} cy={last.y} r="4.5" fill={accent} opacity="0.25" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Headline KPI card
// Hero style (violet gradient) for question_type === 'headline' — the one
// Claude designated as the most important metric for this domain.
// The compiler enforces max 1 headline per dashboard so there is exactly
// one hero card, not "whichever landed at index 0".
// ---------------------------------------------------------------------------
function HeadlineCard({ spec, sessionId, index }: { spec: ChartSpec; sessionId: string; index: number }) {
  const [data, setData] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAggregate(sessionId, spec.x_col, spec.y_col, spec.agg, 1, null)
      .then(rows => {
        if (!cancelled) { setData(rows); setLoading(false) }
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [sessionId, spec.x_col, spec.y_col, spec.agg])

  const isHero = spec.question_type === 'headline'
  const accent = KPI_ACCENTS[index % 4]
  const value = data[0]?.value ?? null

  if (loading) {
    return (
      <div className="rounded-[16px] animate-pulse"
        style={{
          background: isHero ? 'linear-gradient(135deg, #6C47FF, #4F35CC)' : '#fff',
          border: isHero ? 'none' : '1px solid #E8E8F0',
          minHeight: 160,
          boxShadow: isHero
            ? '0 12px 40px -8px rgba(108,71,255,0.45)'
            : '0 1px 3px rgba(11,10,20,0.04), 0 8px 28px -12px rgba(11,10,20,0.08)',
        }} />
    )
  }
  if (value === null) return null

  const fmt = spec.format ?? 'number'

  if (isHero) {
    return (
      <div className="relative overflow-hidden flex flex-col"
        style={{
          background: 'linear-gradient(135deg, #6C47FF 0%, #4F35CC 60%, #3A28B8 100%)',
          borderRadius: 16,
          padding: '22px 20px 16px',
          boxShadow: '0 12px 40px -8px rgba(108,71,255,0.5), 0 4px 12px rgba(108,71,255,0.3)',
        }}>
        <div style={{
          position: 'absolute', top: -30, right: -30, width: 120, height: 120,
          borderRadius: '50%', background: 'rgba(255,255,255,0.06)', pointerEvents: 'none',
        }} />
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', fontWeight: 500, letterSpacing: '0.005em', marginBottom: 4 }}>
          {spec.title}
        </p>
        <p style={{
          fontSize: 36, fontWeight: 700, letterSpacing: '-0.035em',
          color: '#fff', lineHeight: 1.02, marginTop: 8,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {fmtVal(value, fmt, spec.agg)}
        </p>
        {spec.description && (
          <p style={{ fontSize: 11.5, color: 'rgba(255,255,255,0.5)', marginTop: 6, lineHeight: 1.4 }}>
            {spec.description}
          </p>
        )}
        <Sparkline value={value} accent="rgba(255,255,255,0.8)" index={index} />
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden flex flex-col"
      style={{
        background: '#fff',
        borderRadius: 16,
        border: '1px solid #E8E8F0',
        padding: '22px 20px 16px',
        boxShadow: '0 1px 0 rgba(11,10,20,0.03), 0 1px 3px rgba(11,10,20,0.04), 0 8px 28px -12px rgba(11,10,20,0.08)',
      }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 3,
        background: `linear-gradient(90deg, ${accent}, ${accent}88)`,
      }} />
      <p style={{ fontSize: 12, color: '#8B8BA7', fontWeight: 500, letterSpacing: '0.005em', marginBottom: 4 }}>
        {spec.title}
      </p>
      <p style={{
        fontSize: 36, fontWeight: 700, letterSpacing: '-0.035em',
        color: '#1A1A2E', lineHeight: 1.02, marginTop: 8,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {fmtVal(value, fmt, spec.agg)}
      </p>
      {spec.description && (
        <p style={{ fontSize: 11.5, color: '#8B8BA7', marginTop: 6, lineHeight: 1.4 }}>
          {spec.description}
        </p>
      )}
      <Sparkline value={value} accent={accent} index={index} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Standard bar / line chart
// ---------------------------------------------------------------------------
function DynamicChart({ spec, sessionId }: { spec: ChartSpec; sessionId: string }) {
  const [data, setData] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setFailed(false)

    fetchAggregate(
      sessionId,
      spec.x_col,
      spec.y_col,
      spec.agg,
      spec.limit ?? 15,
      spec.time_unit,
    )
      .then(rows => {
        if (cancelled) return
        setData(rows)
        setLoading(false)
      })
      .catch(() => {
        if (!cancelled) { setFailed(true); setLoading(false) }
      })

    return () => { cancelled = true }
  }, [sessionId, spec.x_col, spec.y_col, spec.agg, spec.time_unit])

  if (loading) {
    return (
      <div className="rounded-2xl animate-pulse"
        style={{ background: '#fff', border: '1px solid #E8E8F0', minHeight: 200, padding: 24,
          boxShadow: '0 1px 3px rgba(11,10,20,0.04), 0 8px 28px -12px rgba(11,10,20,0.08)' }}>
        <div className="h-3 w-1/2 rounded mb-2" style={{ background: '#F1F1F7' }} />
        <div className="h-2 w-3/4 rounded mb-6" style={{ background: '#F5F5FA' }} />
        {[80, 65, 50, 40].map((w, i) => (
          <div key={i} className="h-5 rounded mb-2" style={{ width: `${w}%`, background: '#F5F5FA' }} />
        ))}
      </div>
    )
  }

  if (failed || data.length === 0) return null

  const fmt = spec.format ?? 'number'
  const humanY = spec.agg === 'count' ? 'Count' : formatColName(spec.y_col)

  const showDonut = (spec.question_type === 'composition' || spec.question_type === 'ranking') && data.length >= 2 && data.length <= 8
  const showArea  = spec.type === 'line'

  // Donut center label: sum or largest single value
  const donutTotal = data.reduce((s, r) => s + r.value, 0)

  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: '20px 24px 20px',
      border: '1px solid #E8E8F0',
      boxShadow: '0 1px 0 rgba(11,10,20,0.03), 0 1px 3px rgba(11,10,20,0.04), 0 8px 28px -12px rgba(11,10,20,0.08)',
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1A1A2E', marginBottom: 4, letterSpacing: '-0.01em' }}>
        {spec.title}
      </h3>
      {spec.description && (
        <p style={{ fontSize: 12, color: '#8B8BA7', marginBottom: 16 }}>{spec.description}</p>
      )}

      {/* ── Donut chart — composition questions with ≤8 categories ── */}
      {showDonut && (
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <defs>
              <filter id="donut-shadow">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.08" />
              </filter>
            </defs>
            <Pie
              data={data}
              dataKey="value"
              nameKey="label"
              cx="50%"
              cy="45%"
              innerRadius={60}
              outerRadius={95}
              paddingAngle={2}
              strokeWidth={0}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={BAR_PALETTE[i % BAR_PALETTE.length]} />
              ))}
            </Pie>
            {/* Center label */}
            <text x="50%" y="42%" textAnchor="middle" dominantBaseline="middle"
              style={{ fontSize: 20, fontWeight: 700, fill: '#1A1A2E', fontFamily: 'inherit' }}>
              {fmtVal(donutTotal, fmt, spec.agg)}
            </text>
            <text x="50%" y="52%" textAnchor="middle" dominantBaseline="middle"
              style={{ fontSize: 10, fill: '#8B8BA7', fontFamily: 'inherit' }}>
              Total
            </text>
            <Tooltip
              formatter={(v: number, name: string) => [fmtVal(v, fmt, spec.agg), name]}
              contentStyle={TIP_STYLE}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingTop: 8 }}
              formatter={(value, entry) => (
                `${value}: ${fmtVal((entry.payload as { value: number }).value, fmt, spec.agg)}`
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      )}

      {/* ── Area chart — trend questions ── */}
      {!showDonut && showArea && (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 4, right: 20, left: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6C47FF" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#6C47FF" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#8B8BA7' }}
              tickFormatter={v => String(v).length > 8 ? String(v).slice(0, 7) + '…' : String(v)} />
            <YAxis tick={{ fontSize: 10, fill: '#8B8BA7' }} tickFormatter={v => fmtVal(v, fmt, spec.agg)} />
            <Tooltip
              formatter={(v: number) => [fmtVal(v, fmt, spec.agg), humanY]}
              contentStyle={TIP_STYLE}
            />
            <Area
              type="monotone" dataKey="value"
              stroke="#6C47FF" strokeWidth={2}
              fill="url(#areaGrad)"
              dot={{ fill: '#6C47FF', r: 3, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#8666FF' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {/* ── Bar chart — ranking / comparison / fallback ── */}
      {!showDonut && !showArea && (
        <ResponsiveContainer width="100%" height={Math.max(160, data.length * 36)}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 64, left: 8, bottom: 0 }}>
            <XAxis type="number" hide tickFormatter={v => fmtVal(v, fmt, spec.agg)} />
            <YAxis
              type="category" dataKey="label" width={120}
              tick={{ fontSize: 11, fill: '#8B8BA7' }}
              tickFormatter={v => String(v).length > 16 ? String(v).slice(0, 15) + '…' : String(v)}
            />
            <Tooltip
              formatter={(v: number) => [fmtVal(v, fmt, spec.agg), humanY]}
              contentStyle={TIP_STYLE}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}
              label={{
                position: 'right', fontSize: 10, fill: '#8B8BA7',
                formatter: (v: number) => fmtVal(v, fmt, spec.agg),
              }}>
              {data.map((_, i) => <Cell key={i} fill={BAR_PALETTE[i % BAR_PALETTE.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Grid — splits headline cards from charts
// ---------------------------------------------------------------------------
export function DynamicChartGrid({ chartSpecs, sessionId }: DynamicChartGridProps) {
  if (!chartSpecs || chartSpecs.length === 0) return null

  const sorted = [...chartSpecs].sort((a, b) => (a.priority ?? 5) - (b.priority ?? 5))
  const headlines = sorted.filter(s => s.question_type === 'headline')
  const charts = sorted.filter(s => s.question_type !== 'headline')

  return (
    <section>
      {/* Headline KPI cards */}
      {headlines.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {headlines.map((spec, i) => (
            <HeadlineCard key={i} spec={spec} sessionId={sessionId} index={i} />
          ))}
        </div>
      )}

      {/* Charts header */}
      {charts.length > 0 && (
        <>
          <div
            className="flex items-center gap-4 mb-6 p-4 rounded-2xl"
            style={{
              background: 'linear-gradient(135deg, rgba(108,71,255,0.07) 0%, rgba(108,71,255,0.02) 100%)',
              border: '1px solid rgba(108,71,255,0.14)',
            }}
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(108,71,255,0.12)' }}>
              <Sparkles className="w-5 h-5" style={{ color: '#6C47FF' }} />
            </div>
            <div>
              <h2 style={{ fontSize: 17, fontWeight: 800, color: '#1A1A2E', letterSpacing: '-0.015em', lineHeight: 1 }}>
                AI-Selected Charts
              </h2>
              <p style={{ fontSize: 12, color: '#8B8BA7', marginTop: 6 }}>
                Charts chosen by Claude — answering the business questions that matter for this dataset
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {charts.map((spec, i) => (
              <DynamicChart key={i} spec={spec} sessionId={sessionId} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
