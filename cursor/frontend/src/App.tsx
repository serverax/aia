import { useState } from 'react'
import { DashboardPage } from './pages/DashboardPage'
import { EditorPage } from './pages/EditorPage'
import { ApprovalRequestPage } from './pages/ApprovalRequestPage'

function App() {
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
      </nav>
      {activePage === 'dashboard' ? <DashboardPage /> : null}
      {activePage === 'approvals' ? <ApprovalRequestPage /> : null}
      {activePage === 'editor' ? <EditorPage /> : null}
    </>
  )
}

export default App
