import { useEffect, useMemo, useState } from 'react'
import { useDocumentPreview } from './useDocumentPreview'
import { templateService } from '../services/editor/templateService'
import type {
  DocumentContent,
  DocumentMetadata,
  Recommendation,
  Template,
} from '../services/editor/schemas'

const defaultMetadata: DocumentMetadata = {
  author: 'analyst@example.com',
  date: new Date().toISOString().slice(0, 10),
  classification: 'Confidential',
}

export function useEditor(recommendation?: Recommendation) {
  const initialContent: DocumentContent = recommendation
    ? {
        title: recommendation.title,
        executive_summary: recommendation.summary,
        recommendations: recommendation.details,
        policies: recommendation.supporting_policies ?? [],
      }
    : {}

  const [templates, setTemplates] = useState<Template[]>([])
  const [template, setTemplate] = useState<Template | null>(null)
  const [content, setContent] = useState<DocumentContent>(initialContent)
  const [metadata, setMetadata] = useState<DocumentMetadata>(defaultMetadata)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true)
  const { generatePreview } = useDocumentPreview()

  useEffect(() => {
    let mounted = true
    templateService.getTemplates().then((loaded) => {
      if (!mounted) return
      setTemplates(loaded)
      setIsLoadingTemplates(false)
      setTemplate((current) => current ?? loaded[0] ?? null)
    })
    return () => {
      mounted = false
    }
  }, [])

  const preview = useMemo(() => generatePreview(template, content), [template, content, generatePreview])

  return {
    templates,
    isLoadingTemplates,
    template,
    setTemplate,
    content,
    setContent,
    metadata,
    setMetadata,
    preview,
  }
}

