import type { GenerateDocumentRequest, GenerateDocumentResponse, Template } from './schemas'

const baseUrl = import.meta.env.VITE_EDITOR_API_BASE_URL ?? 'http://localhost:8010/api/v1'

export const editorService = {
  async fetchTemplates(): Promise<Template[]> {
    const response = await fetch(`${baseUrl}/templates`)
    if (!response.ok) {
      throw new Error('Unable to load templates')
    }
    return (await response.json()) as Template[]
  },

  async generateDocument(request: GenerateDocumentRequest): Promise<GenerateDocumentResponse> {
    const response = await fetch(`${baseUrl}/generate/${request.format}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    if (!response.ok) {
      throw new Error('Unable to generate document')
    }
    return (await response.json()) as GenerateDocumentResponse
  },

  async renderPreview(templateId: string, content: GenerateDocumentRequest['content']) {
    const response = await fetch(`${baseUrl}/templates/${templateId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) {
      throw new Error('Unable to render preview')
    }
    return (await response.json()) as { preview_html: string }
  },
}

