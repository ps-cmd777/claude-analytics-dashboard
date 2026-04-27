import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InsightsPanel } from './InsightsPanel'
import type { AnalysisResult } from '../types'

const FIXTURE_ANALYSIS: AnalysisResult = {
  executive_summary: 'This e-commerce dataset contains 1,000 transactions across 4 regions.',
  key_findings: [
    'Revenue ranges from $50 to $5,000 with a mean of $820.',
    'West region accounts for 35% of total revenue.',
    'Discount above 20% correlates with negative profit margins.',
  ],
  column_analyses: [
    {
      column_name: 'revenue',
      summary: 'Right-skewed numeric column representing transaction value.',
      quality: 'No missing values. 14 outliers detected above $4,500.',
      patterns: 'Strong positive correlation with profit (r=0.87).',
    },
  ],
  anomalies: ['14 revenue values exceed $4,500 — possible bulk orders or data entry errors.'],
  recommendations: [
    'Investigate the 12 duplicate rows before using this data for modelling.',
    'Apply log transformation to revenue before regression analysis.',
  ],
  methodology_notes: 'Used pandas profiling with IQR outlier detection.',
}

describe('InsightsPanel', () => {
  it('renders null when no analysis and not analyzing', () => {
    const { container } = render(
      <InsightsPanel
        analysis={null}
        streamingText=""
        statusMessage=""
        isAnalyzing={false}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows loading skeleton when analyzing with no text', () => {
    render(
      <InsightsPanel
        analysis={null}
        streamingText=""
        statusMessage="Running tools..."
        isAnalyzing={true}
      />,
    )
    expect(screen.getByText('Running tools...')).toBeInTheDocument()
    expect(screen.getByText('AI Analysis in Progress')).toBeInTheDocument()
  })

  it('shows streaming text while analyzing', () => {
    render(
      <InsightsPanel
        analysis={null}
        streamingText="This dataset has interesting"
        statusMessage=""
        isAnalyzing={true}
      />,
    )
    expect(screen.getByText(/This dataset has interesting/)).toBeInTheDocument()
  })

  it('renders executive summary when analysis is complete', () => {
    render(
      <InsightsPanel
        analysis={FIXTURE_ANALYSIS}
        streamingText=""
        statusMessage=""
        isAnalyzing={false}
      />,
    )
    expect(screen.getByText(/This e-commerce dataset contains 1,000 transactions/)).toBeInTheDocument()
  })

  it('renders key findings section with correct count', () => {
    render(
      <InsightsPanel
        analysis={FIXTURE_ANALYSIS}
        streamingText=""
        statusMessage=""
        isAnalyzing={false}
      />,
    )
    expect(screen.getByText('Key Findings')).toBeInTheDocument()
    expect(screen.getByText(/Revenue ranges from \$50/)).toBeInTheDocument()
  })

  it('renders all section headings', () => {
    render(
      <InsightsPanel
        analysis={FIXTURE_ANALYSIS}
        streamingText=""
        statusMessage=""
        isAnalyzing={false}
      />,
    )
    expect(screen.getByText('Executive Summary')).toBeInTheDocument()
    expect(screen.getByText('Key Findings')).toBeInTheDocument()
    expect(screen.getByText('Anomalies & Data Quality Issues')).toBeInTheDocument()
    expect(screen.getByText('Recommended Actions')).toBeInTheDocument()
    expect(screen.getByText('Column-by-Column Analysis')).toBeInTheDocument()
  })
})
