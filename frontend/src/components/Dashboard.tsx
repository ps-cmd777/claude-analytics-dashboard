import { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { FileText, RotateCcw, Zap, BarChart2, MessageSquare, Sparkles, Pencil, Check, X } from 'lucide-react'
import { ChartGrid } from './ChartGrid'
import { InsightCards } from './InsightCards'
import { InsightsPanel } from './InsightsPanel'
import { ChatInterface } from './ChatInterface'
import { ExportButton } from './ExportButton'
import { FilterBar } from './FilterBar'
import { DynamicChartGrid } from './DynamicChartGrid'
import { useAnalysis } from '../hooks/useAnalysis'
import { fetchFilteredProfile } from '../utils/api'
import type { DataProfile, AnalysisResult } from '../types'

const ANALYSIS_STEPS = [
  { key: 'column',      label: 'Reading column profiles' },
  { key: 'correlation', label: 'Finding correlations' },
  { key: 'outlier',     label: 'Detecting outliers' },
  { key: 'missing',     label: 'Checking missing values' },
  { key: 'format',      label: 'Writing insights & selecting charts' },
]

function AnalysisLoadingPanel({ statusMessage }: { statusMessage: string }) {
  const activeIndex = Math.max(0, ANALYSIS_STEPS.findIndex(s => statusMessage.toLowerCase().includes(s.key)))
  return (
    <div className="flex flex-col items-center justify-center px-8 py-20 text-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.6, ease: 'linear' }}
        className="mb-6"
      >
        <Sparkles className="w-8 h-8 text-accent" />
      </motion.div>
      <h2 className="text-base font-semibold text-text1 mb-1">Claude is analysing your data</h2>
      <p className="text-xs text-text2 mb-10 max-w-xs">
        Building AI-selected charts and insights tailored to this dataset. Takes 30–60 seconds.
      </p>
      <div className="flex flex-col gap-3 w-full max-w-xs text-left">
        {ANALYSIS_STEPS.map((step, i) => {
          const done = i < activeIndex
          const active = i === activeIndex
          return (
            <div key={step.key} className="flex items-center gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[9px] font-bold transition-all
                ${done ? 'bg-accent text-white' : active ? 'border-2 border-accent' : 'border border-[#D1D5DB]'}`}
                style={active ? { boxShadow: '0 0 10px rgba(108,71,255,0.4)' } : {}}>
                {done ? '✓' : ''}
              </div>
              <span className={`text-xs transition-all ${done ? 'text-text3 line-through' : active ? 'text-text1 font-semibold' : 'text-text3'}`}>
                {step.label}
              </span>
              {active && (
                <motion.div animate={{ opacity: [1, 0.2, 1] }} transition={{ repeat: Infinity, duration: 1.2 }}
                  className="w-1.5 h-1.5 rounded-full bg-accent ml-auto flex-shrink-0" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface DashboardProps {
  sessionId: string
  filename: string
  profile: DataProfile
  onReset: () => void
  onAnalysisDone: (result: AnalysisResult) => void
}

export function Dashboard({ sessionId, filename, profile, onReset, onAnalysisDone }: DashboardProps) {
  const { startAnalysis, isAnalyzing, streamingText, statusMessage, analysis, error } = useAnalysis()
  const analysisStarted = useRef(false)
  const [domainEditing, setDomainEditing] = useState(false)
  const [domainInput, setDomainInput] = useState('')
  const [isRerunning, setIsRerunning] = useState(false)

  const handleDomainCorrection = useCallback(async (correctedDomain: string) => {
    setDomainEditing(false)
    setIsRerunning(true)
    await startAnalysis(sessionId, correctedDomain)
    setIsRerunning(false)
  }, [sessionId, startAnalysis])

  function openDomainEdit() {
    setDomainInput(analysis?.domain ?? '')
    setDomainEditing(true)
  }

  function submitDomainEdit() {
    const trimmed = domainInput.trim()
    if (trimmed && trimmed !== analysis?.domain) handleDomainCorrection(trimmed)
    else setDomainEditing(false)
  }

  useEffect(() => { window.scrollTo(0, 0) }, [])

  const [filters, setFilters] = useState<Record<string, string>>({})
  const [filteredProfile, setFilteredProfile] = useState<DataProfile | null>(null)
  const [filterLoading, setFilterLoading] = useState(false)

  const displayProfile = filteredProfile ?? profile

  useEffect(() => {
    if (analysisStarted.current) return
    analysisStarted.current = true
    startAnalysis(sessionId)
  }, [sessionId]) // eslint-disable-line
  useEffect(() => { if (analysis) onAnalysisDone(analysis) }, [analysis, onAnalysisDone])

  const handleFiltersChange = useCallback(async (newFilters: Record<string, string>) => {
    setFilters(newFilters)
    if (Object.keys(newFilters).length === 0) {
      setFilteredProfile(null)
      return
    }
    setFilterLoading(true)
    try {
      const result = await fetchFilteredProfile(sessionId, newFilters)
      setFilteredProfile(result)
    } catch {
      setFilteredProfile(null)
    } finally {
      setFilterLoading(false)
    }
  }, [sessionId])

  const [rows, cols] = displayProfile.shape

  return (
    <div className="flex h-[100dvh] overflow-hidden" style={{ background: '#F4F5F9' }}>

      {/* ══════════════════════════════════════════════════════════
          LEFT SIDEBAR — dark navy for clear visual separation
      ══════════════════════════════════════════════════════════ */}
      <aside
        className="w-[280px] flex-shrink-0 flex flex-col h-full overflow-hidden"
        style={{ background: '#181530', borderRight: '1px solid rgba(255,255,255,0.06)' }}
      >
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-5 py-5"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #6C47FF, #4F35CC)', boxShadow: '0 4px 12px rgba(108,71,255,0.4)' }}>
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span style={{ fontSize: 16, fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>DataLens</span>
        </div>

        {/* Dataset info */}
        <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10 }}>
            Current Dataset
          </p>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(108,71,255,0.25)' }}>
              <FileText className="w-3.5 h-3.5" style={{ color: '#B4A7FF' }} />
            </div>
            <div className="flex-1 min-w-0">
              <p style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF', lineHeight: 1.3 }} className="truncate">{filename}</p>
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>{rows.toLocaleString()} rows · {cols} cols</p>
            </div>
          </div>
          {analysis?.domain && (
            <div className="mt-2.5">
              <span style={{
                fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                background: 'rgba(108,71,255,0.3)', color: '#C4B5FD', border: '1px solid rgba(108,71,255,0.4)',
                display: 'inline-block', maxWidth: '100%',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {analysis.domain}
              </span>
            </div>
          )}
        </div>

        {/* AI Insights — scrollable */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-4 py-3">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, paddingLeft: 2 }}>
              <div style={{
                width: 22, height: 22, borderRadius: 6, flexShrink: 0,
                background: 'linear-gradient(135deg, #6C47FF, #FF6B35)',
                display: 'grid', placeItems: 'center', color: '#fff', fontSize: 11,
              }}>✦</div>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                Claude Analysis
              </span>
              {isAnalyzing && !analysis && (
                <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4,
                  fontSize: 10, color: 'rgba(255,255,255,0.4)', fontWeight: 500 }}>
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#6C47FF', animation: 'pulse 1.2s infinite' }} />
                  Running…
                </span>
              )}
            </div>
            <InsightsPanel
              analysis={analysis}
              streamingText={streamingText}
              statusMessage={statusMessage}
              isAnalyzing={isAnalyzing}
              error={error}
            />
          </div>
        </div>

        {/* Bottom actions */}
        <div className="px-4 py-4 flex flex-col gap-2"
          style={{ borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}>
          {analysis && <ExportButton sessionId={sessionId} filename={filename} />}
          <button
            onClick={onReset}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all"
            style={{ border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.45)',
              background: 'rgba(255,255,255,0.04)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.08)'; (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.75)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.45)' }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Start new analysis
          </button>
        </div>
      </aside>

      {/* ══════════════════════════════════════════════════════════
          MAIN CONTENT
      ══════════════════════════════════════════════════════════ */}
      <div className="flex-1 overflow-y-auto flex flex-col">

        {/* Top bar */}
        <header
          className="flex-shrink-0 flex items-center justify-between px-8 py-4"
          style={{ borderBottom: '1px solid #E5E0D8', background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(12px)' }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', color: '#0F0F1A', lineHeight: 1 }}>
                Dashboard
              </h1>

              {/* Inline domain pill + edit */}
              {analysis?.domain && !domainEditing && !isRerunning && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 999,
                    background: 'rgba(108,71,255,0.08)', color: '#6C47FF',
                    border: '1px solid rgba(108,71,255,0.18)',
                  }}>
                    {analysis.domain}
                  </span>
                  <button
                    onClick={openDomainEdit}
                    title="Correct domain"
                    style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#9CA3AF',
                      background: 'none', border: 'none', cursor: 'pointer', padding: '2px 4px', borderRadius: 4 }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#6C47FF')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#9CA3AF')}
                  >
                    <Pencil style={{ width: 11, height: 11 }} />
                    <span>Not quite right?</span>
                  </button>
                </div>
              )}

              {/* Inline domain edit form */}
              {domainEditing && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input
                    autoFocus
                    value={domainInput}
                    onChange={e => setDomainInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') submitDomainEdit(); if (e.key === 'Escape') setDomainEditing(false) }}
                    placeholder="e.g. Hospital patient records"
                    style={{ fontSize: 12, fontWeight: 500, color: '#0F0F1A', background: '#fff',
                      border: '1.5px solid #6C47FF', borderRadius: 8, padding: '4px 10px', outline: 'none',
                      width: 240, fontFamily: 'inherit', boxShadow: '0 0 0 3px rgba(108,71,255,0.1)' }}
                  />
                  <button onClick={submitDomainEdit} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: 26, height: 26, borderRadius: 6, border: 'none', cursor: 'pointer', background: '#6C47FF', color: '#fff' }}>
                    <Check style={{ width: 12, height: 12 }} />
                  </button>
                  <button onClick={() => setDomainEditing(false)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: 26, height: 26, borderRadius: 6, border: '1px solid #E8E8F0', cursor: 'pointer', background: '#fff', color: '#6B7280' }}>
                    <X style={{ width: 12, height: 12 }} />
                  </button>
                </div>
              )}

              {isRerunning && (
                <span style={{ fontSize: 11, color: '#6C47FF', fontWeight: 500 }}>Re-analysing…</span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-1">
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>
                {rows.toLocaleString()} rows · {cols} cols
              </span>
              <span style={{ width: 3, height: 3, borderRadius: '50%', background: '#D1D5DB', display: 'inline-block' }} />
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>
                {displayProfile.numeric_columns.length} numeric · {displayProfile.categorical_columns.length} categorical
              </span>
              {filteredProfile && (
                <>
                  <span style={{ width: 3, height: 3, borderRadius: '50%', background: '#D1D5DB', display: 'inline-block' }} />
                  <span style={{ fontSize: 12, color: '#6C47FF', fontWeight: 600 }}>filtered</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isAnalyzing && !analysis && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 12, fontWeight: 500, color: '#6C47FF',
                background: 'rgba(108,71,255,0.07)', padding: '6px 12px',
                borderRadius: 999, border: '1px solid rgba(108,71,255,0.15)',
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#6C47FF', animation: 'pulse 1.2s infinite' }} />
                Analysing…
              </div>
            )}
            {analysis && <ExportButton sessionId={sessionId} filename={filename} />}
          </div>
        </header>

        {/* Filters */}
        <FilterBar
          originalProfile={profile}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          loading={filterLoading}
        />

        {/* Insight Cards — 4 fixed slots: headline / risk / trend / action */}
        {analysis?.insight_cards && analysis.insight_cards.length > 0 && (
          <InsightCards cards={analysis.insight_cards} />
        )}

        {/* Analysis loading */}
        {isAnalyzing && !analysis && <AnalysisLoadingPanel statusMessage={statusMessage} />}

        {/* AI-Selected Charts — backend-compiled specs, no frontend quality gate */}
        {analysis?.chart_specs && analysis.chart_specs.length > 0 && (
          <div className="px-8 pt-8 pb-6">
            <DynamicChartGrid chartSpecs={analysis.chart_specs} sessionId={sessionId} />
          </div>
        )}

        {/* Column Distributions */}
        {analysis && (
          <div className="px-8 pb-6">
            <SectionLabel
              icon={BarChart2}
              title="Column Distributions"
              sub="Statistical breakdown of every column — distributions, correlations, and missing data"
            />
            <ChartGrid profile={displayProfile} skipDistributions={new Set(analysis.skip_distributions ?? [])} />
          </div>
        )}

        {/* Chat */}
        <div className="px-8 pb-12">
          <div className="max-w-2xl mx-auto">
            <SectionLabel
              icon={MessageSquare}
              title="Chat with your data"
              sub="Claude has full context — ask anything about your dataset"
            />
            <ChatInterface sessionId={sessionId} analysis={analysis} />
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionLabel({ icon: Icon, title, sub }: { icon: React.ElementType; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-4 mb-6 p-4 rounded-2xl"
      style={{
        background: 'linear-gradient(135deg, rgba(108,71,255,0.07) 0%, rgba(108,71,255,0.02) 100%)',
        border: '1px solid rgba(108,71,255,0.14)',
      }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: 'rgba(108,71,255,0.12)' }}>
        <Icon className="w-5 h-5" style={{ color: '#6C47FF' }} />
      </div>
      <div className="flex-1 min-w-0">
        <h2 className="text-[17px] font-[800] text-[#0F0F1A] tracking-tight leading-none">{title}</h2>
        {sub && <p className="text-[12px] text-[#9CA3AF] mt-1.5 leading-relaxed">{sub}</p>}
      </div>
    </div>
  )
}
