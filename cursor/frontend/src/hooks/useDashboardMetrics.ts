import { useMemo } from 'react'
import type { OrchestratorMetrics } from '../types/api'
import { useOrchestratorAPI } from './useOrchestratorAPI'

const emptyMetrics: OrchestratorMetrics = {
  tasks_completed: 0,
  tasks_pending: 0,
  avg_approval_time_ms: 0,
}

export function useDashboardMetrics() {
  const { snapshot } = useOrchestratorAPI()

  const metrics = useMemo(() => snapshot?.metrics ?? emptyMetrics, [snapshot?.metrics])

  return metrics
}

