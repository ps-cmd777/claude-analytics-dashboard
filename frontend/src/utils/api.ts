import type { DataProfile, SSEEvent, UploadResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

export async function uploadCSV(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail ?? 'Upload failed')
  }

  return res.json() as Promise<UploadResponse>
}

// ---------------------------------------------------------------------------
// SSE stream reader
// ---------------------------------------------------------------------------

/**
 * Reads a fetch Response body as a Server-Sent Events stream.
 * Calls `onEvent` for each parsed SSE payload, then resolves.
 */
export async function readSSEStream(
  response: Response,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.body) throw new Error('Response has no body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      if (signal?.aborted) break

      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE events are separated by double newlines
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        for (const line of part.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const payload = JSON.parse(line.slice(6)) as SSEEvent
            onEvent(payload)
          } catch {
            // Malformed line — skip
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// ---------------------------------------------------------------------------
// Analyze
// ---------------------------------------------------------------------------

export async function fetchAnalysis(
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
  domainHint?: string,
): Promise<void> {
  const url = new URL(`${API_BASE}/api/analyze/${sessionId}`, window.location.href)
  if (domainHint) url.searchParams.set('domain_hint', domainHint)
  const res = await fetch(url.toString(), {
    headers: { Accept: 'text/event-stream' },
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Analysis failed' }))
    throw new Error(err.detail ?? 'Analysis failed')
  }

  return readSSEStream(res, onEvent, signal)
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function fetchChat(
  sessionId: string,
  message: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ message }),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }))
    throw new Error(err.detail ?? 'Chat failed')
  }

  return readSSEStream(res, onEvent, signal)
}

// ---------------------------------------------------------------------------
// Export URL
// ---------------------------------------------------------------------------

export function exportUrl(sessionId: string): string {
  return `${API_BASE}/api/export/${sessionId}`
}

// ---------------------------------------------------------------------------
// Aggregate — fetch grouped data for dynamic charts
// ---------------------------------------------------------------------------

export async function fetchAggregate(
  sessionId: string,
  groupCol: string,
  metricCol: string,
  agg: string,
  limit: number = 15,
  timeUnit?: string | null,
): Promise<{ label: string; value: number }[]> {
  const res = await fetch(`${API_BASE}/api/aggregate/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      group_col: groupCol,
      metric_col: metricCol,
      agg,
      limit,
      time_unit: timeUnit ?? null,
    }),
  })
  if (!res.ok) throw new Error('Aggregation failed')
  const json = await res.json()
  return json.data as { label: string; value: number }[]
}

// ---------------------------------------------------------------------------
// Filter
// ---------------------------------------------------------------------------

export async function fetchFilteredProfile(
  sessionId: string,
  filters: Record<string, string>,
): Promise<DataProfile> {
  const res = await fetch(`${API_BASE}/api/filter/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filters }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Filter failed' }))
    throw new Error(err.detail ?? 'Filter failed')
  }

  return res.json() as Promise<DataProfile>
}
