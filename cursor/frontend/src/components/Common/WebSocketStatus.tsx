interface WebSocketStatusProps {
  isConnected: boolean
  label: string
}

export function WebSocketStatus({ isConnected, label }: WebSocketStatusProps) {
  return (
    <div className="status-chip" aria-live="polite">
      <span className={`status-dot ${isConnected ? 'online' : 'offline'}`} />
      <span>{label}</span>
    </div>
  )
}

