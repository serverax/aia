import { useState } from 'react'
import { editorService } from '../services/editor/editorService'
import type {
  DocumentContent,
  DocumentMetadata,
  GenerateDocumentResponse,
} from '../services/editor/schemas'

interface GenerateInput {
  templateId: string
  content: DocumentContent
  metadata: DocumentMetadata
  format: 'docx' | 'pdf'
}

export function useDocumentGenerator() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateDocument = async (input: GenerateInput): Promise<GenerateDocumentResponse | null> => {
    setIsGenerating(true)
    setError(null)
    try {
      return await editorService.generateDocument({
        template_id: input.templateId,
        content: input.content,
        metadata: input.metadata,
        format: input.format,
      })
    } catch {
      setError('Document generation failed. Confirm editor API is running.')
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  return { generateDocument, isGenerating, error }
}

