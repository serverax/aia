interface DocumentPreviewProps {
  html: string
  isLoading: boolean
}

export function DocumentPreview({ html, isLoading }: DocumentPreviewProps) {
  return (
    <section className="card editor-section">
      <h2>Preview</h2>
      {isLoading ? <p className="loading">Generating preview...</p> : null}
      <div className="preview-html" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  )
}

