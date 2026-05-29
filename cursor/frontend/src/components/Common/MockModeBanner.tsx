import { isMockEnabled } from '../../services/orchestrator/client'

/**
 * Visible warning shown whenever the app runs on MOCK data
 * (VITE_ENABLE_MOCKS=true, dev only). Renders nothing in real mode.
 * `enabled` is injectable for tests; defaults to the runtime flag.
 */
export function MockModeBanner({ enabled = isMockEnabled }: { enabled?: boolean }) {
  if (!enabled) return null
  return (
    <div
      role="alert"
      style={{
        background: '#b45309',
        color: '#fff',
        padding: '6px 12px',
        textAlign: 'center',
        fontWeight: 600,
        fontSize: 13,
      }}
    >
      ⚠️ MOCK MODE — dashboard and approvals show synthetic data, not the real backend.
    </div>
  )
}

export default MockModeBanner
