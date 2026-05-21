import { useState } from 'react'
import { DashboardPage } from './pages/DashboardPage'
import { EditorPage } from './pages/EditorPage'

function App() {
  const [activePage, setActivePage] = useState<'dashboard' | 'editor'>('dashboard')

  return (
    <>
      <nav className="top-nav">
        <button type="button" onClick={() => setActivePage('dashboard')}>
          Dashboard
        </button>
        <button type="button" onClick={() => setActivePage('editor')}>
          Editor
        </button>
      </nav>
      {activePage === 'dashboard' ? <DashboardPage /> : <EditorPage />}
    </>
  )
}

export default App
