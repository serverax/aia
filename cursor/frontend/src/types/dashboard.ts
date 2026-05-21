import type { OrchestratorMetrics, OrchestratorTask } from './api'

export interface DashboardState {
  metrics: OrchestratorMetrics
  tasks: OrchestratorTask[]
}

