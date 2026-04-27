// ── Column / Profile ──────────────────────────────────────────────────────────

export interface ColumnProfile {
  name: string
  dtype: string
  missing_count: number
  missing_pct: number
  unique_count: number
  semantic_role: string
  mean: number | null
  median: number | null
  std: number | null
  min_val: number | null
  max_val: number | null
  q25: number | null
  q75: number | null
  outlier_count: number
  top_values: Record<string, number>
  date_min: string | null
  date_max: string | null
  date_range_days: number | null
}

export interface DataProfile {
  shape: [number, number]
  columns: string[]
  column_profiles: Record<string, ColumnProfile>
  numeric_columns: string[]
  categorical_columns: string[]
  date_columns: string[]
  total_missing: number
  total_missing_pct: number
  correlation_matrix: Record<string, Record<string, number>>
  duplicate_rows: number
  memory_usage_mb: number
  relationships: Record<string, string>[]
}

// ── Analysis result ────────────────────────────────────────────────────────────

export interface ColumnAnalysis {
  column_name: string
  summary: string
  quality: string
  patterns: string
}

export interface ChartSpec {
  type: 'bar' | 'line' | 'headline'
  question_type?: 'headline' | 'ranking' | 'trend' | 'composition' | 'comparison'
  title: string
  description?: string
  x_col: string
  y_col: string
  agg: 'sum' | 'mean' | 'median' | 'count' | 'count_distinct'
  sort?: 'asc' | 'desc' | 'none'
  limit?: number | null
  time_unit?: 'month' | 'quarter' | 'year' | 'auto' | null
  format?: 'currency' | 'percent' | 'number' | 'integer'
  priority?: number
}

export interface AnalysisResult {
  executive_summary: string
  key_findings: string[]
  column_analyses: ColumnAnalysis[]
  anomalies: string[]
  recommendations: string[]
  methodology_notes: string
  chart_specs: ChartSpec[]
  skip_distributions: string[]
  domain: string
  grain: string
  practitioner_persona: string
  insight_cards: InsightCard[]
}

export interface InsightCard {
  type: 'headline' | 'risk' | 'trend' | 'action'
  icon: 'target' | 'alert' | 'trending-up' | 'lightbulb'
  label: string
  title: string
  body: string
  supporting_columns: string[]
}

// ── SSE events ────────────────────────────────────────────────────────────────

export interface SSEStatusEvent {
  type: 'status'
  message: string
}

export interface SSETokenEvent {
  type: 'token'
  text: string
}

export interface SSEDoneEvent {
  type: 'done'
  result?: AnalysisResult
}

export interface SSEErrorEvent {
  type: 'error'
  message: string
}

export type SSEEvent = SSEStatusEvent | SSETokenEvent | SSEDoneEvent | SSEErrorEvent

// ── Upload / session ──────────────────────────────────────────────────────────

export interface UploadResponse {
  session_id: string
  filename: string
  profile: DataProfile
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

// ── App state ─────────────────────────────────────────────────────────────────

export type AppPhase =
  | 'idle'       // no file uploaded
  | 'uploading'  // POST /api/upload in progress
  | 'analyzing'  // SSE stream open for /analyze
  | 'done'       // analysis complete, chat enabled
  | 'error'

export interface AppState {
  phase: AppPhase
  sessionId: string | null
  filename: string | null
  profile: DataProfile | null
  analysis: AnalysisResult | null
  streamingText: string
  statusMessage: string
  chatMessages: ChatMessage[]
  error: string | null
}
