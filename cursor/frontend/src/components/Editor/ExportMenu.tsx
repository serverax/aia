import { useEffect, useState } from 'react'
import { useDocumentGenerator } from '../../hooks/useDocumentGenerator'
import type { DocumentContent, DocumentMetadata, Template } from '../../services/editor/schemas'

interface ExportMenuProps {
  template: Template | null
  content: DocumentContent
  metadata: DocumentMetadata
}

export function ExportMenu({ template, content, metadata }: ExportMenuProps) {
  const { generateDocument, isGenerating, error } = useDocumentGenerator()
  const [downloadStatus, setDownloadStatus] = useState<'idle' | 'generating' | 'success' | 'error'>(
    'idle',
  )

  const handleExport = async (format: 'docx' | 'pdf') => {
    if (!template) return
    setDownloadStatus('generating')
    const generated = await generateDocument({
      templateId: template.id,
      content,
      metadata,
      format,
    })
    if (!generated) {
      setDownloadStatus('error')
      return
    }
    const anchor = document.createElement('a')
    anchor.href = `${import.meta.env.VITE_EDITOR_API_HOST ?? 'http://localhost:8010'}${generated.file_url}`
    anchor.download = `${generated.id}.${generated.format}`
    anchor.click()
    setDownloadStatus('success')
  }

  useEffect(() => {
    if (downloadStatus !== 'success') return
    const timeout = window.setTimeout(() => setDownloadStatus('idle'), 3000)
    return () => window.clearTimeout(timeout)
  }, [downloadStatus])

  return (
    <section className="card editor-section">
      <h2>Export</h2>
      <div className="export-menu">
        <button type="button" onClick={() => handleExport('docx')} disabled={!template || isGenerating}>
          Download DOCX
        </button>
        <button type="button" onClick={() => handleExport('pdf')} disabled={!template || isGenerating}>
          Download PDF
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {downloadStatus === 'generating' ? <p className="loading">Generating document...</p> : null}
      {downloadStatus === 'success' ? <p className="success">✓ Downloaded successfully</p> : null}
      {downloadStatus === 'error' ? <p className="error">✗ Download failed</p> : null}
    </section>
  )
}

