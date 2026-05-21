import type { Template } from './schemas'

const baseUrl = import.meta.env.VITE_EDITOR_API_BASE_URL ?? 'http://localhost:8010/api/v1'

const fallbackTemplates: Template[] = [
  {
    id: 'risk_assessment',
    name: 'Risk Assessment Report',
    version: '1.0',
    description: 'Standard risk assessment document',
    sections: [
      { type: 'title', field: 'title', required: true, placeholder: 'Assessment title' },
      {
        type: 'text',
        field: 'executive_summary',
        required: true,
        placeholder: 'Executive summary (2-3 sentences)',
      },
      {
        type: 'table',
        field: 'risk_matrix',
        columns: ['Risk', 'Probability', 'Impact', 'Score'],
        rows: 'dynamic',
      },
      {
        type: 'text',
        field: 'recommendations',
        required: true,
        placeholder: 'Key recommendations',
      },
      {
        type: 'references',
        field: 'policies',
        source: 'semantic_search',
        placeholder: 'Linked compliance policies',
      },
    ],
    styling: {
      font: 'Arial',
      font_size: 11,
      line_spacing: 1.15,
      colors: { header: '#003366', accent: '#0066CC' },
    },
  },
  {
    id: 'policy_memo',
    name: 'Policy Memo',
    version: '1.0',
    description: 'Summarize policy changes and rationale.',
    sections: [
      { type: 'title', field: 'title', required: true, placeholder: 'Policy memo title' },
      { type: 'text', field: 'context', required: true, placeholder: 'Policy context' },
      { type: 'text', field: 'recommendations', required: true, placeholder: 'Recommendations' },
      { type: 'references', field: 'policies', source: 'semantic_search' },
    ],
    styling: { font: 'Arial', font_size: 11, line_spacing: 1.15, colors: { header: '#003366' } },
  },
  {
    id: 'incident_report',
    name: 'Incident Report',
    version: '1.0',
    description: 'Capture and communicate incident details and mitigations.',
    sections: [
      { type: 'title', field: 'title', required: true, placeholder: 'Incident report title' },
      { type: 'text', field: 'incident_summary', required: true, placeholder: 'Incident summary' },
      { type: 'text', field: 'impact_assessment', required: true, placeholder: 'Business impact' },
      { type: 'table', field: 'timeline', columns: ['Time', 'Event', 'Owner'], rows: 'dynamic' },
      { type: 'references', field: 'policies', source: 'semantic_search' },
    ],
    styling: { font: 'Arial', font_size: 11, line_spacing: 1.15, colors: { header: '#532d13' } },
  },
  {
    id: 'compliance_checklist',
    name: 'Compliance Checklist',
    version: '1.0',
    description: 'Checklist-style compliance validation report.',
    sections: [
      { type: 'title', field: 'title', required: true, placeholder: 'Checklist title' },
      { type: 'table', field: 'checklist_items', columns: ['Requirement', 'Status', 'Owner'], rows: 'dynamic' },
      { type: 'text', field: 'notes', placeholder: 'Additional notes' },
      { type: 'references', field: 'policies', source: 'semantic_search' },
    ],
    styling: { font: 'Arial', font_size: 11, line_spacing: 1.15, colors: { header: '#2a4b7c' } },
  },
  {
    id: 'audit_summary',
    name: 'Audit Summary',
    version: '1.0',
    description: 'Executive summary for internal or external audits.',
    sections: [
      { type: 'title', field: 'title', required: true, placeholder: 'Audit summary title' },
      { type: 'text', field: 'scope', required: true, placeholder: 'Audit scope' },
      { type: 'text', field: 'findings', required: true, placeholder: 'Top findings' },
      { type: 'text', field: 'recommendations', required: true, placeholder: 'Actions and owners' },
      { type: 'references', field: 'policies', source: 'semantic_search' },
    ],
    styling: { font: 'Arial', font_size: 11, line_spacing: 1.15, colors: { header: '#0d5c48' } },
  },
]

export const templateService = {
  async getTemplates(): Promise<Template[]> {
    try {
      const response = await fetch(`${baseUrl}/templates`)
      if (!response.ok) {
        return fallbackTemplates
      }
      return (await response.json()) as Template[]
    } catch {
      return fallbackTemplates
    }
  },
}

