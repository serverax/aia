import type { Template } from '../../services/editor/schemas'

interface TemplateSelectorProps {
  selected: Template | null
  templates: Template[]
  loading: boolean
  onSelect: (template: Template) => void
}

export function TemplateSelector({ selected, templates, loading, onSelect }: TemplateSelectorProps) {
  return (
    <section className="card editor-section">
      <h2>Template</h2>
      <label htmlFor="template-select">Document Template</label>
      <select
        id="template-select"
        value={selected?.id ?? ''}
        onChange={(event) => {
          const picked = templates.find((item) => item.id === event.target.value)
          if (picked) onSelect(picked)
        }}
        disabled={loading}
      >
        <option value="">Choose a template...</option>
        {templates.map((template) => (
          <option key={template.id} value={template.id}>
            {template.name}
          </option>
        ))}
      </select>
      {loading ? <p className="loading">Loading templates...</p> : null}
      {selected ? (
        <div className="template-preview">
          <p>{selected.description}</p>
          <ul>
            {selected.sections.map((section) => (
              <li key={section.field}>
                {section.field} ({section.type})
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

