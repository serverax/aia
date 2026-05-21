import { useMemo } from 'react'
import type { ApprovalWorkflowRequest } from '../types/api'

function durationMs(startIso: string, endIso: string) {
  return Math.max(0, new Date(endIso).getTime() - new Date(startIso).getTime())
}

export function useApprovalMetrics(requests: ApprovalWorkflowRequest[]) {
  const metrics = useMemo(() => {
    if (requests.length === 0) {
      return {
        avgCycleHours: 0,
        slaComplianceRate: 0,
        reviewerRanking: [] as Array<{ reviewer: string; avgHours: number }>,
        bottlenecks: [] as ApprovalWorkflowRequest[],
      }
    }

    const completed = requests.filter((request) => request.status === 'approved' || request.status === 'rejected')
    const cycleSamples = completed.map((request) => {
      const latestSignoff =
        request.reviewers
          .map((reviewer) => reviewer.signed_at)
          .filter(Boolean)
          .sort()
          .at(-1) ?? request.requested_at
      return durationMs(request.requested_at, latestSignoff) / (1000 * 60 * 60)
    })

    const avgCycleHours =
      cycleSamples.length > 0
        ? Number((cycleSamples.reduce((sum, value) => sum + value, 0) / cycleSamples.length).toFixed(2))
        : 0

    const referenceMs = Math.max(...requests.map((request) => new Date(request.requested_at).getTime()))
    const slaOnTrack = requests.filter((request) => new Date(request.deadline).getTime() >= referenceMs).length
    const slaComplianceRate = Number(((slaOnTrack / requests.length) * 100).toFixed(1))

    const reviewerDurations = new Map<string, number[]>()
    requests.forEach((request) => {
      request.reviewers.forEach((reviewer) => {
        if (!reviewer.signed_at) return
        const hours = durationMs(request.requested_at, reviewer.signed_at) / (1000 * 60 * 60)
        reviewerDurations.set(reviewer.user_id, [...(reviewerDurations.get(reviewer.user_id) ?? []), hours])
      })
    })

    const reviewerRanking = Array.from(reviewerDurations.entries())
      .map(([reviewer, values]) => ({
        reviewer,
        avgHours: Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2)),
      }))
      .sort((a, b) => a.avgHours - b.avgHours)

    const bottlenecks = requests
      .filter((request) => request.status === 'pending' || request.status === 'in_progress')
      .filter((request) => new Date(request.deadline).getTime() < referenceMs + 4 * 60 * 60 * 1000)

    return {
      avgCycleHours,
      slaComplianceRate,
      reviewerRanking,
      bottlenecks,
    }
  }, [requests])

  return metrics
}

