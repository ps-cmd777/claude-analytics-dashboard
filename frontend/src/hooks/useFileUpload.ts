import { useState, useCallback } from 'react'
import { uploadCSV } from '../utils/api'
import type { UploadResponse } from '../types'

interface UseFileUploadReturn {
  upload: (file: File) => Promise<UploadResponse>
  isUploading: boolean
  error: string | null
  clearError: () => void
}

export function useFileUpload(): UseFileUploadReturn {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const upload = useCallback(async (file: File): Promise<UploadResponse> => {
    setIsUploading(true)
    setError(null)
    try {
      const result = await uploadCSV(file)
      return result
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setError(msg)
      throw err
    } finally {
      setIsUploading(false)
    }
  }, [])

  const clearError = useCallback(() => setError(null), [])

  return { upload, isUploading, error, clearError }
}
