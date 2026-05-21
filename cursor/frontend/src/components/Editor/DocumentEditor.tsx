import { PolicyReferenceWidget } from './PolicyReferenceWidget'
import type {
  DocumentContent,
  PolicyReference,
  TableRow,
  Template,
  TemplateSection,
} from '../../services/editor/schemas'

interface DocumentEditorProps {
  template: Template | null
  content: DocumentContent
  onChange: (content: DocumentContent) => void
}

interface EditorFieldProps {
  section: TemplateSection
  value: DocumentContent[string]
  onChange: (value: DocumentContent[string]) => void
}

function TableEditor({
  columns,
  value,
  onChange,
}: {
  columns: string[]
  value: TableRow[]
  onChange: (rows: TableRow[]) => void
}) {
  const updateCell = (rowIndex: number, column: string, cellValue: string) => {
    const next = value.map((row, index) =>
      index === rowIndex
        ? {
            ...row,
            [column]: cellValue,
          }
        : row,
    )
    onChange(next)
  }

  const addRow = () => {
    const emptyRow: TableRow = {}
    columns.forEach((column) => {
      emptyRow[column] = ''
    })
    onChange([...value, emptyRow])
  }

  return (
    <div className="table-editor">
      <button type="button" onClick={addRow}>
        Add Row
      </button>
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {value.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {columns.map((column) => (
                <td key={`${rowIndex}-${column}`}>
                  <input
                    value={String(row[column] ?? '')}
                    onChange={(event) => updateCell(rowIndex, column, event.target.value)}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EditorField({ section, value, onChange }: EditorFieldProps) {
  if (section.type === 'title' || section.type === 'text') {
    return (
      <textarea
        className="editor-input"
        placeholder={section.placeholder}
        value={String(value ?? '')}
        onChange={(event) => onChange(event.target.value)}
        rows={section.type === 'title' ? 1 : 4}
      />
    )
  }

  if (section.type === 'table') {
    return (
      <TableEditor
        columns={section.columns ?? []}
        value={(value as TableRow[] | undefined) ?? []}
        onChange={(rows) => onChange(rows)}
      />
    )
  }

  if (section.type === 'references') {
    return (
      <PolicyReferenceWidget
        value={(value as PolicyReference[] | undefined) ?? []}
        onChange={(references) => onChange(references)}
      />
    )
  }

  return null
}

export function DocumentEditor({ template, content, onChange }: DocumentEditorProps) {
  if (!template) {
    return (
      <section className="card editor-section">
        <h2>Document Editor</h2>
        <p>Select a template first.</p>
      </section>
    )
  }

  return (
    <section className="card editor-section">
      <h2>Document Editor</h2>
      <div className="editor-form">
        {template.sections.map((section) => (
          <div key={section.field} className="editor-field">
            <label>{section.field}</label>
            <EditorField
              section={section}
              value={content[section.field]}
              onChange={(nextValue) =>
                onChange({
                  ...content,
                  [section.field]: nextValue,
                })
              }
            />
          </div>
        ))}
      </div>
    </section>
  )
}

