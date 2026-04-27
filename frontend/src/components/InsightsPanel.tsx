import { motion } from 'framer-motion'
import { Zap, TrendingUp, AlertTriangle, Lightbulb } from 'lucide-react'
import type { AnalysisResult } from '../types'

function LoadingSkeleton({ statusMessage }: { statusMessage: string }) {
  const steps = [
    { label: 'Reading column profiles', key: 'column' },
    { label: 'Finding correlations',    key: 'correlation' },
    { label: 'Detecting outliers',      key: 'outlier' },
    { label: 'Checking missing values', key: 'missing' },
    { label: 'Writing insights',        key: 'format' },
  ]
  const activeIndex = Math.max(0, steps.findIndex(s => statusMessage.toLowerCase().includes(s.key)))

  return (
    <div className="py-3">
      <div className="flex items-center gap-2 mb-4">
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.4, ease: 'linear' }}>
          <Zap className="w-3.5 h-3.5" style={{ color: '#6C47FF' }} />
        </motion.div>
        <span className="text-[12px] font-[700]" style={{ color: '#fff' }}>Claude is analysing…</span>
      </div>
      <div className="space-y-2.5">
        {steps.map((step, i) => {
          const done = i < activeIndex
          const active = i === activeIndex
          return (
            <div key={i} className="flex items-center gap-2.5">
              <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 text-[9px] font-bold transition-all ${done ? 'text-white' : ''}`}
                style={{
                  background: done ? '#6C47FF' : 'transparent',
                  border: done ? 'none' : active ? '2px solid #6C47FF' : '1.5px solid rgba(255,255,255,0.2)',
                  boxShadow: active ? '0 0 8px rgba(108,71,255,0.35)' : 'none',
                }}>
                {done ? '✓' : ''}
              </div>
              <span className={`text-[11px] transition-all ${done ? 'line-through' : ''}`}
                style={{ color: done ? 'rgba(255,255,255,0.3)' : active ? '#fff' : 'rgba(255,255,255,0.5)', fontWeight: active ? 600 : 400 }}>
                {step.label}
              </span>
              {active && (
                <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ repeat: Infinity, duration: 1.2 }}
                  className="w-1 h-1 rounded-full ml-auto flex-shrink-0" style={{ background: '#6C47FF' }} />
              )}
            </div>
          )
        })}
      </div>
      <p className="text-[10px] mt-4" style={{ color: 'rgba(180,167,255,0.6)' }}>Takes 30–60 seconds.</p>
    </div>
  )
}

const SECTIONS = [
  {
    id: 'findings',
    label: 'Key Findings',
    icon: TrendingUp,
    accent: '#6C47FF',
    accentBg: 'rgba(108,71,255,0.12)',
    border: 'rgba(108,71,255,0.22)',
    itemBorder: '#6C47FF',
  },
  {
    id: 'flags',
    label: 'Data Quality Flags',
    icon: AlertTriangle,
    accent: '#F59E0B',
    accentBg: 'rgba(245,158,11,0.1)',
    border: 'rgba(245,158,11,0.2)',
    itemBorder: '#F59E0B',
  },
  {
    id: 'recs',
    label: 'Next Steps',
    icon: Lightbulb,
    accent: '#10B981',
    accentBg: 'rgba(16,185,129,0.1)',
    border: 'rgba(16,185,129,0.2)',
    itemBorder: '#10B981',
  },
] as const

interface InsightsPanelProps {
  analysis: AnalysisResult | null
  streamingText: string
  statusMessage: string
  isAnalyzing: boolean
  error?: string | null
}

export function InsightsPanel({ analysis, statusMessage, isAnalyzing, error }: InsightsPanelProps) {
  if (error && !analysis) {
    return (
      <div className="py-3">
        <div className="rounded-xl px-3 py-3"
          style={{ background: 'rgba(255,71,87,0.06)', border: '1px solid rgba(255,71,87,0.2)' }}>
          <p className="text-[11px] font-[700] text-[#FF4757] mb-1">Analysis failed</p>
          <p className="text-[10px] leading-relaxed" style={{ color: 'rgba(255,71,87,0.75)' }}>{error}</p>
        </div>
      </div>
    )
  }

  if (isAnalyzing && !analysis) return <LoadingSkeleton statusMessage={statusMessage} />
  if (!analysis) return null

  const cleanSummary = analysis.executive_summary.replace(/\*\*/g, '').replace(/\*/g, '')
  const sentences = cleanSummary.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 15)
  const shortSummary = sentences.slice(0, 3).join(' ')

  const sectionData = {
    findings: analysis.key_findings.slice(0, 5),
    flags:    analysis.anomalies.slice(0, 4),
    recs:     analysis.recommendations.slice(0, 4),
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}
      className="space-y-4">

      {/* Summary */}
      <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 14 }}>
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-1 h-3 rounded-full" style={{ background: '#B4A7FF' }} />
          <p className="text-[10px] font-[700] uppercase tracking-widest" style={{ color: '#B4A7FF' }}>Summary</p>
        </div>
        <p className="text-[11.5px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.75)' }}>{shortSummary}</p>
      </div>

      {/* Sections */}
      {SECTIONS.map(sec => {
        const Icon = sec.icon
        const items = sectionData[sec.id]
        if (items.length === 0) return null

        return (
          <div key={sec.id}>
            {/* Section header */}
            <div className="flex items-center gap-2 mb-2.5">
              <Icon style={{ width: 12, height: 12, color: sec.accent, flexShrink: 0 }} />
              <span style={{ fontSize: 10, fontWeight: 800, color: sec.accent, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {sec.label}
              </span>
              <span style={{
                fontSize: 9, fontWeight: 800, padding: '1px 5px', borderRadius: 999,
                background: sec.accentBg, color: sec.accent, border: `1px solid ${sec.border}`,
              }}>
                {items.length}
              </span>
            </div>

            {/* Items */}
            <div className="space-y-2">
              {items.map((item, i) => {
                const clean = item.replace(/\*\*/g, '').replace(/\*/g, '').trim()
                const parts = clean.split(/\s+[—–]\s+/)
                const headline = parts[0]?.trim() ?? clean
                const subtext  = parts[1]?.trim() ?? ''

                return (
                  <div key={i} style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderLeft: `3px solid ${sec.itemBorder}`,
                    borderRadius: '0 10px 10px 0',
                    padding: '9px 12px 9px 10px',
                  }}>
                    <p style={{ fontSize: 11.5, fontWeight: 700, color: '#FFFFFF', lineHeight: 1.35 }}>{headline}</p>
                    {subtext && (
                      <p style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5, marginTop: 3 }}>{subtext}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </motion.div>
  )
}
