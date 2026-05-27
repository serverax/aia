import { useState } from 'react'

import { AuthProvider, useAuth } from './auth/AuthContext'
import { AuthGate } from './components/auth/AuthGate'
import { MockModeBanner } from './components/Common/MockModeBanner'
import { DashboardPage } from './pages/DashboardPage'
import { EditorPage } from './pages/EditorPage'
import { ApprovalRequestPage } from './pages/ApprovalRequestPage'

function AppShell() {
  const { user, signOut } = useAuth()
  const [activePage, setActivePage] = useState<'dashboard' | 'approvals' | 'editor'>('dashboard')

  return (
    <>
      <nav className="top-nav">
        <button type="button" onClick={() => setActivePage('dashboard')}>
          Dashboard
        </button>
        <button type="button" onClick={() => setActivePage('approvals')}>
          Approvals
        </button>
        <button type="button" onClick={() => setActivePage('editor')}>
          Editor
        </button>
        <span style={{ marginLeft: 'auto' }} />
        <span aria-label="current-user" style={{ marginRight: 12 }}>
          {user?.username}
        </span>
        <button type="button" onClick={signOut}>
          Log out
        </button>
      </nav>
      {activePage === 'dashboard' ? <DashboardPage /> : null}
      {activePage === 'approvals' ? <ApprovalRequestPage /> : null}
      {activePage === 'editor' ? <EditorPage /> : null}
    </>
  )
}

function App() {
  return (
    <AuthProvider>
      <MockModeBanner />
      <AuthGate>
        <AppShell />
      </AuthGate>
    </AuthProvider>
  )
}

export default App
