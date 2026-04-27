import { useState, useRef, useCallback } from 'react'
import LandingLayout from './components/layout/LandingLayout'
import { Dashboard } from './components/Dashboard'
import { useFileUpload } from './hooks/useFileUpload'
import type { UploadResponse, AnalysisResult } from './types'

export default function App() {
  const [upload, setUpload] = useState<UploadResponse | null>(null)
  const [, setAnalysis] = useState<AnalysisResult | null>(null)
  const { upload: doUpload, isUploading, error } = useFileUpload()
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(async (file: File) => {
    try { await doUpload(file).then(setUpload) } catch { /* captured in hook */ }
  }, [doUpload])

  const handleUploadTrigger = useCallback(() => {
    inputRef.current?.click()
  }, [])

  if (upload) {
    return (
      <Dashboard
        sessionId={upload.session_id}
        filename={upload.filename}
        profile={upload.profile}
        onReset={() => { setUpload(null); setAnalysis(null) }}
        onAnalysisDone={setAnalysis}
      />
    )
  }

  return (
    <>
      <LandingLayout onUpload={handleUploadTrigger} />
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = '' }}
      />
      {isUploading && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl px-8 py-6 text-center shadow-2xl">
            <p className="text-sm font-semibold text-gray-800 mb-1">Uploading your file…</p>
            <p className="text-xs text-gray-500">This only takes a moment</p>
          </div>
        </div>
      )}
      {error && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-red-500 text-white text-sm px-5 py-3 rounded-xl shadow-lg z-50">
          {error}
        </div>
      )}
    </>
  )
}
