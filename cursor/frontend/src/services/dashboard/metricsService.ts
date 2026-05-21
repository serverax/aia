import { orchestratorClient } from '../orchestrator'

export const metricsService = {
  async getMetrics() {
    const snapshot = await orchestratorClient.getSnapshot()
    return snapshot.metrics
  },
}

