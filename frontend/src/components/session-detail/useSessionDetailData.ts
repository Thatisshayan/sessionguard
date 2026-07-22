/**
 * src/components/session-detail/useSessionDetailData.ts
 * --------------------------------------------------------
 * React Query v5 data layer for SessionDetail. Replaces the old
 * useEffect + Promise.all fetch-on-mount pattern: each resource is its
 * own deduped, cached query, and mutations invalidate precisely instead
 * of manually patching local state.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSession, getInsights, getAlerts, getReviewQueue,
  getSessionEvents, getEventsSummary, getSessionBehavior,
  acknowledgeAlert, resolveReviewItem, createExport, getExports,
  startLiveRun, getLiveRun, stopLiveRun,
} from '../../services/api'

const keys = {
  session:  (id: number) => ['session', id] as const,
  insights: (id: number) => ['session', id, 'insights'] as const,
  alerts:   (id: number) => ['session', id, 'alerts'] as const,
  queue:    (id: number) => ['session', id, 'review-queue'] as const,
  events:   (id: number) => ['session', id, 'events'] as const,
  evSummary:(id: number) => ['session', id, 'events-summary'] as const,
  behavior: (id: number) => ['session', id, 'behavior'] as const,
  exports:  (id: number) => ['session', id, 'exports'] as const,
}

export function useSessionDetailData(sessionId: number) {
  const qc = useQueryClient()
  const enabled = Number.isFinite(sessionId)

  const session   = useQuery({ queryKey: keys.session(sessionId),   queryFn: () => getSession(sessionId),   enabled })
  const insights  = useQuery({ queryKey: keys.insights(sessionId),  queryFn: () => getInsights(sessionId),  enabled })
  const alerts    = useQuery({ queryKey: keys.alerts(sessionId),    queryFn: () => getAlerts({ session_id: sessionId }), enabled })
  const queue     = useQuery({ queryKey: keys.queue(sessionId),     queryFn: () => getReviewQueue({ session_id: sessionId, status: 'pending' }), enabled })
  const events    = useQuery({ queryKey: keys.events(sessionId),    queryFn: () => getSessionEvents(sessionId), enabled })
  const evSummary = useQuery({ queryKey: keys.evSummary(sessionId), queryFn: () => getEventsSummary(sessionId), enabled })
  const behavior  = useQuery({ queryKey: keys.behavior(sessionId),  queryFn: () => getSessionBehavior(sessionId), enabled, retry: false })
  const exports_  = useQuery({ queryKey: keys.exports(sessionId),   queryFn: () => getExports(sessionId),   enabled })

  const ackMutation = useMutation({
    mutationFn: (alertId: number) => acknowledgeAlert(alertId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.alerts(sessionId) }),
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => resolveReviewItem(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.queue(sessionId) }),
  })

  const exportMutation = useMutation({
    mutationFn: (fmt: string) => createExport(fmt, sessionId),
    onSuccess: (r: any) => {
      qc.invalidateQueries({ queryKey: keys.exports(sessionId) })
      if (r?.export_id) window.open(`http://127.0.0.1:8000/exports/${r.export_id}/download`, '_blank')
    },
  })

  const startLiveMutation = useMutation({
    mutationFn: async () => {
      const r = await startLiveRun({ session_id: sessionId, mode: 'mock', tick_interval: 2.0 })
      return getLiveRun(r.run_id)
    },
  })

  const stopLiveMutation = useMutation({
    mutationFn: (runId: number) => stopLiveRun(runId),
  })

  const loading = enabled && [session, insights, alerts, queue, events, evSummary, exports_].some(q => q.isPending)
  const error = [session, insights, alerts, queue, events, evSummary, exports_]
    .map(q => q.error)
    .find(Boolean) as any

  return {
    session: session.data, insights: insights.data ?? [], alerts: alerts.data ?? [],
    queue: queue.data ?? [], events: events.data?.events ?? [], evSummary: evSummary.data,
    behavior: behavior.data ?? null, exports: exports_.data ?? [],
    loading, error: error?.message,
    acknowledge:   ackMutation.mutateAsync,
    resolve:       (id: number, action: string) => resolveMutation.mutateAsync({ id, action }),
    createExport:  exportMutation.mutateAsync,
    exporting:     exportMutation.isPending ? (exportMutation.variables ?? '') : '',
    startLive:     startLiveMutation.mutateAsync,
    stopLive:      stopLiveMutation.mutateAsync,
  }
}
