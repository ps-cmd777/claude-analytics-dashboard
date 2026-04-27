import { Target, AlertTriangle, TrendingUp, Lightbulb } from 'lucide-react'
import { motion } from 'framer-motion'
import type { InsightCard } from '../types'

interface InsightCardsProps {
  cards: InsightCard[]
}

const CONFIG = {
  headline: {
    icon: Target,
    bg: 'rgba(108,71,255,0.08)',
    border: 'rgba(108,71,255,0.18)',
    iconBg: 'rgba(108,71,255,0.14)',
    iconColor: '#6C47FF',
    labelColor: '#6C47FF',
  },
  risk: {
    icon: AlertTriangle,
    bg: 'rgba(239,68,68,0.06)',
    border: 'rgba(239,68,68,0.16)',
    iconBg: 'rgba(239,68,68,0.1)',
    iconColor: '#EF4444',
    labelColor: '#EF4444',
  },
  trend: {
    icon: TrendingUp,
    bg: 'rgba(0,200,150,0.06)',
    border: 'rgba(0,200,150,0.16)',
    iconBg: 'rgba(0,200,150,0.1)',
    iconColor: '#00C896',
    labelColor: '#00A87D',
  },
  action: {
    icon: Lightbulb,
    bg: 'rgba(255,184,0,0.06)',
    border: 'rgba(255,184,0,0.18)',
    iconBg: 'rgba(255,184,0,0.1)',
    iconColor: '#D97706',
    labelColor: '#D97706',
  },
} as const

export function InsightCards({ cards }: InsightCardsProps) {
  if (!cards || cards.length === 0) return null

  // Enforce canonical order: headline → risk → trend → action
  const ORDER = ['headline', 'risk', 'trend', 'action']
  const sorted = ORDER
    .map(type => cards.find(c => c.type === type))
    .filter((c): c is InsightCard => c !== undefined)

  return (
    <div className="px-8 pt-6 pb-2">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {sorted.map((card, i) => {
          const cfg = CONFIG[card.type] ?? CONFIG.headline
          const Icon = cfg.icon
          return (
            <motion.div
              key={card.type}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              style={{
                background: '#FFFFFF',
                border: `1px solid #EAECF0`,
                borderRadius: 16,
                padding: '18px 20px',
                boxShadow: '0 1px 3px rgba(11,10,20,0.04), 0 4px 16px -4px rgba(11,10,20,0.06)',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                borderTop: `3px solid ${cfg.iconColor}`,
              }}
            >
              {/* Icon + label */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                  background: cfg.iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon className="w-3.5 h-3.5" style={{ color: cfg.iconColor }} />
                </div>
                <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.08em',
                  textTransform: 'uppercase', color: cfg.labelColor }}>
                  {card.label}
                </span>
              </div>

              {/* Title */}
              <p style={{ fontSize: 13, fontWeight: 700, color: '#0F0F1A', lineHeight: 1.35 }}>
                {card.title}
              </p>

              {/* Body */}
              <p style={{ fontSize: 11.5, color: '#6B7280', lineHeight: 1.55, marginTop: 'auto' }}>
                {card.body}
              </p>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
