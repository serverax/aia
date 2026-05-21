import { EditorPanel } from '../components/Editor'
import type { Recommendation } from '../services/editor/schemas'

const seededRecommendation: Recommendation = {
  title: 'Q2 2026 Risk Assessment',
  summary:
    'Critical data handling controls require additional verification across customer data workflows.',
  details:
    'Prioritize encryption key rotation automation, tighten incident triage SLAs, and schedule quarterly policy conformance audits.',
  supporting_policies: [
    {
      id: 'DOC_001',
      title: 'Data Protection Policy',
      url: 'https://example.local/policies/data-protection',
      jurisdiction: 'UK',
    },
  ],
}

export function EditorPage() {
  return (
    <main className="dashboard-layout">
      <header className="dashboard-header">
        <div>
          <h1>Editor Agent</h1>
          <p>Build formatted compliance documents from analyst recommendations.</p>
        </div>
      </header>
      <EditorPanel recommendation={seededRecommendation} />
    </main>
  )
}

