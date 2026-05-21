import { useCallback } from 'react'
import type { DocumentContent, PolicyReference, TableRow, Template } from '../services/editor/schemas'

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

export function useDocumentPreview() {
  const generatePreview = useCallback((template: Template | null, content: DocumentContent) => {
    if (!template) return '<p>Select a template to start.</p>'

    const blocks = template.sections.map((section) => {
      const value = content[section.field]
      if (section.type === 'title') {
        return `<h1>${escapeHtml(String(value ?? section.placeholder ?? 'Untitled Document'))}</h1>`
      }

      if (section.type === 'text') {
        const text = escapeHtml(String(value ?? section.placeholder ?? ''))
        return `<section><h3>${escapeHtml(section.field)}</h3><p>${text.replaceAll('\n', '<br/>')}</p></section>`
      }

      if (section.type === 'table') {
        const rows = (value as TableRow[] | undefined) ?? []
        const columns = section.columns ?? []
        const header = columns.map((col) => `<th>${escapeHtml(col)}</th>`).join('')
        const body =
          rows.length === 0
            ? `<tr><td colspan="${columns.length || 1}">No rows</td></tr>`
            : rows
                .map(
                  (row) =>
                    `<tr>${columns
                      .map((col) => `<td>${escapeHtml(String(row[col] ?? ''))}</td>`)
                      .join('')}</tr>`,
                )
                .join('')
        return `<section><h3>${escapeHtml(section.field)}</h3><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></section>`
      }

      const policies = (value as PolicyReference[] | undefined) ?? []
      const policyRows =
        policies.length === 0
          ? '<li>No references selected.</li>'
          : policies
              .map(
                (policy) =>
                  `<li>${escapeHtml(policy.title)}${policy.jurisdiction ? ` (${escapeHtml(policy.jurisdiction)})` : ''}</li>`,
              )
              .join('')
      return `<section><h3>${escapeHtml(section.field)}</h3><ul>${policyRows}</ul></section>`
    })

    return `<article>${blocks.join('')}</article>`
  }, [])

  return { generatePreview }
}

