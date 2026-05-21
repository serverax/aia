import type { ReactNode } from 'react'
import { WebSocketStatus } from '../Common/WebSocketStatus'

interface DashboardLayoutProps {
  children: ReactNode
  connected: boolean
  connectionLabel: string
  onReconnectTest?: () => void
}

export function DashboardLayout({
  children,
  connected,
  connectionLabel,
  onReconnectTest,
}: DashboardLayoutProps) {
  return (
    <main className="dashboard-layout">
      <header className="dashboard-header">
        <div>
          <h1>Glass Box Dashboard</h1>
          <p>Monitor orchestrator activity and resolve human approvals.</p>
        </div>
        <div className="header-actions">
          {onReconnectTest ? (
            <button type="button" onClick={onReconnectTest}>
              Reconnect Test
            </button>
          ) : null}
          <WebSocketStatus isConnected={connected} label={connectionLabel} />
        </div>
      </header>
      {children}
    </main>
  )
}

