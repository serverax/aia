import { useMemo, useState } from 'react'
import { ReviewerSelector } from './ReviewerSelector'
import type { ApprovalRequestType, ApprovalWorkflowRequest, CreateApprovalWorkflowInput } from '../../types/api'

interface ApprovalRequestFormProps {
  onCreate: (input: CreateApprovalWorkflowInput) => Promise<ApprovalWorkflowRequest | null>
  isSubmitting: boolean
}

type ApprovalTemplatePreset = {
  id: string
  label: string
  requestType: ApprovalRequestType
  strategy: 'all_must_approve' | 'any_can_approve' | 'weighted_voting'
  reviewers: string[]
  riskScore: string
  title: string
  description: string
  deadlineHours: number
}

const approvalTemplatePresets: ApprovalTemplatePreset[] = [
  {
    id: 'policy-standard',
    label: 'Policy Change Standard Review',
    requestType: 'policy_change',
    strategy: 'all_must_approve',
    reviewers: ['you@synthetic.io', 'compliance_officer@synthetic.io'],
    riskScore: '7.0',
    title: 'Policy Change Review',
    description: 'Review policy deltas, verify compliance mapping, and approve rollout readiness.',
    deadlineHours: 36,
  },
  {
    id: 'exception-fastlane',
    label: 'Exception Fastlane',
    requestType: 'exception',
    strategy: 'all_must_approve',
    reviewers: ['you@synthetic.io', 'security_lead@synthetic.io'],
    riskScore: '8.3',
    title: 'Security Exception Request',
    description: 'Validate exception scope, compensating controls, and rollback criteria.',
    deadlineHours: 12,
  },
  {
    id: 'document-release',
    label: 'Document Release',
    requestType: 'document_release',
    strategy: 'any_can_approve',
    reviewers: ['you@synthetic.io', 'editor@synthetic.io'],
    riskScore: '5.4',
    title: 'Document Release Approval',
    description: 'Confirm classification and approve release to external audience.',
    deadlineHours: 24,
  },
]

export function ApprovalRequestForm({ onCreate, isSubmitting }: ApprovalRequestFormProps) {
  const [createdAtBaseline] = useState(() => new Date().toISOString())
  const [selectedTemplateId, setSelectedTemplateId] = useState('custom')
  const [requestType, setRequestType] = useState<ApprovalRequestType>('policy_change')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [relatedDocumentId, setRelatedDocumentId] = useState('')
  const [riskScore, setRiskScore] = useState('5')
  const [reviewerInput, setReviewerInput] = useState('')
  const [reviewers, setReviewers] = useState<string[]>(['you@synthetic.io'])
  const [deadline, setDeadline] = useState('')
  const [strategy, setStrategy] = useState<'all_must_approve' | 'any_can_approve' | 'weighted_voting'>(
    'all_must_approve',
  )
  const [createMessage, setCreateMessage] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const slaHours = useMemo(() => {
    if (!deadline) return null
    const delta = new Date(deadline).getTime() - new Date(createdAtBaseline).getTime()
    return Number((delta / (1000 * 60 * 60)).toFixed(1))
  }, [createdAtBaseline, deadline])

  const addReviewer = () => {
    const value = reviewerInput.trim().toLowerCase()
    if (!value || reviewers.includes(value)) return
    setReviewers([...reviewers, value])
    setReviewerInput('')
  }

  const applyTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId)
    if (templateId === 'custom') return
    const template = approvalTemplatePresets.find((item) => item.id === templateId)
    if (!template) return
    const deadlineDate = new Date(new Date(createdAtBaseline).getTime() + template.deadlineHours * 60 * 60 * 1000)
    const deadlineValue = deadlineDate.toISOString().slice(0, 16)
    setRequestType(template.requestType)
    setStrategy(template.strategy)
    setReviewers(template.reviewers)
    setRiskScore(template.riskScore)
    setTitle(template.title)
    setDescription(template.description)
    setDeadline(deadlineValue)
    setCreateMessage(`Template applied: ${template.label}`)
  }

  const submit = async () => {
    const errors: string[] = []
    if (!title.trim()) errors.push('Title is required.')
    if (!description.trim()) errors.push('Description is required.')
    if (reviewers.length === 0) errors.push('At least one reviewer is required.')
    if (!deadline) errors.push('Deadline is required.')
    if (deadline) {
      const target = new Date(deadline).getTime()
      if (Number.isNaN(target) || target <= new Date(createdAtBaseline).getTime()) {
        errors.push('Deadline must be in the future.')
      }
    }

    setValidationErrors(errors)
    if (errors.length > 0) {
      setCreateMessage('Please correct validation errors before submitting.')
      return
    }
    const created = await onCreate({
      request_type: requestType,
      title,
      description,
      deadline: new Date(deadline).toISOString(),
      reviewers,
      approval_strategy: strategy,
      metadata: {
        related_document_id: relatedDocumentId || undefined,
        risk_score: Number(riskScore),
      },
    })
    if (!created) {
      setCreateMessage('Unable to create request.')
      return
    }
    setCreateMessage(`Created request ${created.id}.`)
    setTitle('')
    setDescription('')
    setRelatedDocumentId('')
    setRiskScore('5')
    setDeadline('')
    setReviewers(['you@synthetic.io'])
    setSelectedTemplateId('custom')
  }

  return (
    <section className="card approval-card">
      <h2>Create Approval Request</h2>
      <div className="approval-form-block">
        <label>Request Template</label>
        <select value={selectedTemplateId} onChange={(event) => applyTemplate(event.target.value)}>
          <option value="custom">Custom</option>
          {approvalTemplatePresets.map((template) => (
            <option key={template.id} value={template.id}>
              {template.label}
            </option>
          ))}
        </select>
      </div>
      <div className="approval-form-block">
        <label>Request Type</label>
        <select value={requestType} onChange={(event) => setRequestType(event.target.value as ApprovalRequestType)}>
          <option value="policy_change">policy_change</option>
          <option value="document_release">document_release</option>
          <option value="exception">exception</option>
        </select>
      </div>

      <div className="approval-form-block">
        <label>Title</label>
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </div>

      <div className="approval-form-block">
        <label>Description</label>
        <textarea value={description} rows={4} onChange={(event) => setDescription(event.target.value)} />
      </div>

      <div className="approval-form-grid">
        <div className="approval-form-block">
          <label>Related Document ID</label>
          <input value={relatedDocumentId} onChange={(event) => setRelatedDocumentId(event.target.value)} />
        </div>
        <div className="approval-form-block">
          <label>Risk Score</label>
          <input type="number" step="0.1" value={riskScore} onChange={(event) => setRiskScore(event.target.value)} />
        </div>
      </div>

      <ReviewerSelector
        reviewerInput={reviewerInput}
        reviewers={reviewers}
        deadline={deadline}
        strategy={strategy}
        onReviewerInputChange={setReviewerInput}
        onAddReviewer={addReviewer}
        onRemoveReviewer={(reviewer) => setReviewers(reviewers.filter((item) => item !== reviewer))}
        onDeadlineChange={setDeadline}
        onStrategyChange={setStrategy}
      />

      <p className="loading">{slaHours !== null ? `SLA countdown: ${slaHours} hours` : 'Set deadline for SLA countdown.'}</p>
      <button type="button" onClick={submit} disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create Request'}
      </button>
      {validationErrors.length > 0 ? (
        <ul className="error-list">
          {validationErrors.map((error) => (
            <li key={error} className="error">
              {error}
            </li>
          ))}
        </ul>
      ) : null}
      {createMessage ? <p className="success">{createMessage}</p> : null}
    </section>
  )
}

