import { useEditor } from '../../hooks/useEditor'
import type { Recommendation } from '../../services/editor/schemas'
import { DocumentEditor } from './DocumentEditor'
import { DocumentPreview } from './DocumentPreview'
import { ExportMenu } from './ExportMenu'
import { TemplateSelector } from './TemplateSelector'

interface EditorPanelProps {
  recommendation?: Recommendation
}

export function EditorPanel({ recommendation }: EditorPanelProps) {
  const {
    templates,
    isLoadingTemplates,
    template,
    setTemplate,
    content,
    setContent,
    metadata,
    preview,
  } = useEditor(recommendation)

  return (
    <section className="editor-container">
      <div className="editor-left">
        <TemplateSelector
          selected={template}
          templates={templates}
          loading={isLoadingTemplates}
          onSelect={setTemplate}
        />
        <DocumentEditor template={template} content={content} onChange={setContent} />
      </div>
      <div className="editor-right">
        <DocumentPreview html={preview} isLoading={isLoadingTemplates} />
        <ExportMenu template={template} content={content} metadata={metadata} />
      </div>
    </section>
  )
}

