import { Download } from 'lucide-react'
import { exportUrl } from '../utils/api'

interface ExportButtonProps { sessionId: string; filename: string }

export function ExportButton({ sessionId, filename }: ExportButtonProps) {
  const stem = filename.replace(/\.csv$/i, '')
  return (
    <a
      href={exportUrl(sessionId)}
      download={`report_${stem}.md`}
      className="btn-mag inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white transition-all"
      style={{ background: '#0057FF', boxShadow: '0 0 20px rgba(0,87,255,0.3)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 0 28px rgba(0,87,255,0.5)' }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 0 20px rgba(0,87,255,0.3)' }}
    >
      <Download className="w-3.5 h-3.5" />
      Export report
    </a>
  )
}
