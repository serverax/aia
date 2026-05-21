import { useMemo, useState } from 'react'
import type { PolicyEvaluation, OrchestratorTask } from '../../types/api'

interface PolicyTransparencyLayerProps {
  tasks: OrchestratorTask[]
}

export function PolicyTransparencyLayer({ tasks }: PolicyTransparencyLayerProps) {
  const policies = useMemo(
    () =>
      tasks.flatMap((task) =>
        (task.policy_evaluations ?? []).map((policy) => ({
          ...policy,
          taskId: task.id,
          taskType: task.type,
        })),
      ),
    [tasks],
  )

  const matched = policies.filter((policy) => policy.outcome === 'matched')
  const rejected = policies.filter((policy) => policy.outcome === 'rejected')

  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(policies[0]?.policy_id ?? null)
  const selectedPolicy = policies.find((policy) => policy.policy_id === selectedPolicyId)

  const renderPolicyRow = (policy: PolicyEvaluation & { taskId: string; taskType: string }) => (
    <li key={`${policy.policy_id}-${policy.taskId}`}>
      <div>
        <strong>{policy.title}</strong>
        <p>{policy.source}</p>
      </div>
      <button type="button" onClick={() => setSelectedPolicyId(policy.policy_id)}>
        View policy
      </button>
    </li>
  )

  return (
    <section className="card policy-layer">
      <h2>Policy Transparency Layer</h2>
      <div className="policy-counts">
        <span className="pill approve">Matched: {matched.length}</span>
        <span className="pill reject">Rejected: {rejected.length}</span>
      </div>

      <div className="policy-grid">
        <div>
          <h3>Matched Policies</h3>
          <ul className="policy-list">
            {matched.length > 0 ? matched.map(renderPolicyRow) : <li>No matched policies.</li>}
          </ul>
          <h3>Rejected Policies</h3>
          <ul className="policy-list">
            {rejected.length > 0 ? rejected.map(renderPolicyRow) : <li>No rejected policies.</li>}
          </ul>
        </div>

        <aside className="policy-detail">
          <h3>View Policy</h3>
          {!selectedPolicy ? <p>Select a policy to view details.</p> : null}
          {selectedPolicy ? (
            <>
              <p>
                <strong>{selectedPolicy.title}</strong>
              </p>
              <p>Source: {selectedPolicy.source}</p>
              <p>Outcome: {selectedPolicy.outcome}</p>
              <p>Evaluated by: {selectedPolicy.evaluated_by}</p>
              <p>Task: {selectedPolicy.taskType}</p>
              <p>Rationale: {selectedPolicy.rationale}</p>
              {selectedPolicy.url ? (
                <a href={selectedPolicy.url} target="_blank" rel="noreferrer">
                  Open source
                </a>
              ) : null}
            </>
          ) : null}
        </aside>
      </div>
    </section>
  )
}

