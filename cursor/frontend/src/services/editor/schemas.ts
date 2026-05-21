export type TemplateSectionType = 'title' | 'text' | 'table' | 'references'

export interface TemplateSection {
  type: TemplateSectionType
  field: string
  required?: boolean
  placeholder?: string
  columns?: string[]
  rows?: 'dynamic' | number
  source?: string
}

export interface TemplateStyling {
  font: string
  font_size: number
  line_spacing: number
  colors?: {
    header?: string
    accent?: string
  }
}

export interface Template {
  id: string
  name: string
  version: string
  description: string
  sections: TemplateSection[]
  styling: TemplateStyling
}

export interface PolicyReference {
  id: string
  title: string
  url?: string
  jurisdiction?: string
}

export type TableRow = Record<string, string | number>

export type DocumentContent = Record<string, string | TableRow[] | PolicyReference[]>

export interface DocumentMetadata {
  author: string
  date: string
  classification: 'Public' | 'Internal' | 'Confidential'
}

export interface GenerateDocumentRequest {
  template_id: string
  content: DocumentContent
  metadata: DocumentMetadata
  format: 'docx' | 'pdf'
}

export interface GenerateDocumentResponse {
  id: string
  template_id: string
  format: 'docx' | 'pdf'
  file_url: string
  generated_at: string
  size_bytes: number
  preview_html?: string
}

export interface Recommendation {
  title: string
  summary: string
  details: string
  supporting_policies?: PolicyReference[]
}

