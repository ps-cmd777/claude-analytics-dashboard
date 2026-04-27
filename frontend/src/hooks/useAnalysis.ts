import { useState, useCallback, useRef } from 'react'
import { fetchAnalysis } from '../utils/api'
import type { AnalysisResult, SSEEvent } from '../types'

interface UseAnalysisReturn {
  startAnalysis: (sessionId: string, domainHint?: string) => Promise<void>
  isAnalyzing: boolean
  streamingText: string
  statusMessage: string
  analysis: AnalysisResult | null
  error: string | null
  reset: () => void
}

export function useAnalysis(): UseAnalysisReturn {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [statusMessage, setStatusMessage] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const startAnalysis = useCallback(async (sessionId: string, domainHint?: string) => {
    // Cancel any in-progress stream
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setIsAnalyzing(true)
    setStreamingText('')
    setStatusMessage('Starting analysis...')
    setAnalysis(null)
    setError(null)

    try {
      await fetchAnalysis(
        sessionId,
        (event: SSEEvent) => {
          if (event.type === 'status') {
            setStatusMessage(event.message)
          } else if (event.type === 'token') {
            setStreamingText(prev => prev + event.text)
          } else if (event.type === 'done') {
            if (event.result) {
              setAnalysis(event.result)
            }
            setStatusMessage('')
          } else if (event.type === 'error') {
            setError(event.message)
          }
        },
        controller.signal,
        domainHint,
      )
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError(err instanceof Error ? err.message : 'Analysis failed')
      }
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setIsAnalyzing(false)
    setStreamingText('')
    setStatusMessage('')
    setAnalysis(null)
    setError(null)
  }, [])

  return { startAnalysis, isAnalyzing, streamingText, statusMessage, analysis, error, reset }
}
