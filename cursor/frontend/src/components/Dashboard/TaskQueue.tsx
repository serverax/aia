import { useMemo, useState } from 'react'
import type { OrchestratorTask, TaskStatus } from '../../types/api'

interface TaskQueueProps {
  tasks: OrchestratorTask[]
  highlightedTaskIds: string[]
}

export function TaskQueue({ tasks, highlightedTaskIds }: TaskQueueProps) {
  const [statusFilter, setStatusFilter] = useState<'all' | TaskStatus>('all')
  const [ownerFilter, setOwnerFilter] = useState<'all' | string>('all')
  const [sortBy, setSortBy] = useState<'created' | 'progress' | 'status'>('created')

  const owners = useMemo(
    () => Array.from(new Set(tasks.map((task) => task.created_by))).sort(),
    [tasks],
  )

  const filteredAndSorted = useMemo(() => {
    const filtered = tasks.filter((task) => {
      const matchesStatus = statusFilter === 'all' || task.status === statusFilter
      const matchesOwner = ownerFilter === 'all' || task.created_by === ownerFilter
      return matchesStatus && matchesOwner
    })

    return filtered.sort((a, b) => {
      if (sortBy === 'progress') return (b.progress ?? 0) - (a.progress ?? 0)
      if (sortBy === 'status') return a.status.localeCompare(b.status)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  }, [tasks, ownerFilter, sortBy, statusFilter])

  return (
    <section className="card">
      <h2>Task Queue</h2>
      <div className="task-controls">
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as 'all' | TaskStatus)}>
          <option value="all">All statuses</option>
          <option value="pending">pending</option>
          <option value="in_progress">in_progress</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="completed">completed</option>
        </select>
        <select value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)}>
          <option value="all">All owners</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </select>
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value as 'created' | 'progress' | 'status')}>
          <option value="created">Sort: newest</option>
          <option value="progress">Sort: progress</option>
          <option value="status">Sort: status</option>
        </select>
      </div>
      <ul className="task-list">
        {filteredAndSorted.map((task) => (
          <li key={task.id} className={highlightedTaskIds.includes(task.id) ? 'task-flash' : ''}>
            <div className="task-header">
              <strong>{task.type}</strong>
              <span className={`pill ${task.status}`}>{task.status}</span>
            </div>
            <p>{task.approval_reason || 'No approval reason currently attached.'}</p>
            <small>
              Owner: {task.created_by} | Pending approvals: {task.approvals_pending.length}
            </small>
            <small>Progress: {Math.round((task.progress ?? 0) * 100)}%</small>
          </li>
        ))}
      </ul>
    </section>
  )
}

