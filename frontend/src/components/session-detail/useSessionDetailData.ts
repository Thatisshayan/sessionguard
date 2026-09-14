/**
 * src/components/session-detail/useSessionDetailData.ts
 * --------------------------------------------------------
 * React Query v5 data layer for SessionDetail. Replaces the old
 * useEffect + Promise.all fetch-on-mount pattern: each resource is its
 * own deduped, cached query, and mutations invalidate precisely instead
 * of manually patching local state.
 */

import { useQuery, useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import {
  getSession, getInsights, getAlerts, getReviewQueue,
  getSessionEvents, getEventsSummary, getSessionBehavior,
  acknowledgeAlert, resolveReviewItem, createExport, getExports, getExportDownloadUrl,
  startLiveRun, getLiveRun, stopLiveRun,
  createEvidence, verifyEvidence, validateSessionEvents, explainAlert,
} from '../../services/api'
import { toast } from '../Toast'

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

/** All mutations for SessionDetail, split out to keep useSessionDetailData short. */
function useSessionDetailMutations(sessionId: number, qc: QueryClient) {
  const ackMutation = useMutation({
    mutationFn: (alertId: number) => acknowledgeAlert(alertId),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: keys.alerts(sessionId) }); toast.success('Alert acknowledged') },
    onError: () => { toast.error('Failed to acknowledge alert') },
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => resolveReviewItem(id, action),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: keys.queue(sessionId) }); toast.success('Review item resolved') },
    onError: () => { toast.error('Failed to resolve review item') },
  })

  const exportMutation = useMutation({
    mutationFn: (fmt: string) => createExport(fmt, sessionId),
    onSuccess: (r: { export_id?: number }) => {
      void qc.invalidateQueries({ queryKey: keys.exports(sessionId) })
      toast.success('Export generated')
      if (r.export_id) window.open(getExportDownloadUrl(r.export_id), '_blank')
    },
    onError: () => { toast.error('Export failed') },
  })

  const startLiveMutation = useMutation({
    mutationFn: async () => {
      const r = await startLiveRun({ session_id: sessionId, mode: 'mock', tick_interval: 2.0 })
      return getLiveRun(r.run_id)
    },
  })

  const stopLiveMutation = useMutation({ mutationFn: (runId: number) => stopLiveRun(runId) })

  const evidenceMutation = useMutation({
    mutationFn: () => createEvidence(sessionId),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: keys.exports(sessionId) }); toast.success('Evidence package generated') },
    onError: () => { toast.error('Evidence package generation failed') },
  })

  const verifyEvidenceMutation = useMutation({
    mutationFn: () => verifyEvidence(sessionId),
    onSuccess: (r: { manifest_verified?: Record<string, string> }) => {
      const statuses = Object.values(r.manifest_verified ?? {})
      const badCount = statuses.filter(s => s !== 'ok').length
      toast[badCount ? 'error' : 'success'](badCount ? `Manifest check found ${badCount} file(s) not ok` : 'Manifest verified — all files intact')
    },
    onError: () => { toast.error('Manifest verification failed') },
  })

  const validateEventsMutation = useMutation({
    mutationFn: () => validateSessionEvents(sessionId),
    onError: () => { toast.error('Event validation failed') },
  })

  const explainAlertMutation = useMutation({
    mutationFn: (alertId: number) => explainAlert(alertId),
    onError: () => { toast.error('Failed to generate alert explanation') },
  })

  return {
    ackMutation, resolveMutation, exportMutation, startLiveMutation, stopLiveMutation,
    evidenceMutation, verifyEvidenceMutation, validateEventsMutation, explainAlertMutation,
  }
}

export function useSessionDetailData(sessionId: number) {
  const qc = useQueryClient()
  const enabled = Number.isFinite(sessionId)

  const session   = useQuery({ queryKey: keys.session(sessionId),   queryFn: () => getSession(sessionId),   enabled })
  const insights  = useQuery({ queryKey: keys.insights(sessionId),  queryFn: () => getInsights({ session_id: sessionId }),  enabled })
  const alerts    = useQuery({ queryKey: keys.alerts(sessionId),    queryFn: () => getAlerts({ session_id: sessionId }), enabled })
  const queue     = useQuery({ queryKey: keys.queue(sessionId),     queryFn: () => getReviewQueue({ session_id: sessionId, status: 'pending' }), enabled })
  const events    = useQuery({ queryKey: keys.events(sessionId),    queryFn: () => getSessionEvents(sessionId), enabled })
  const evSummary = useQuery({ queryKey: keys.evSummary(sessionId), queryFn: () => getEventsSummary(sessionId), enabled })
  const behavior  = useQuery({ queryKey: keys.behavior(sessionId),  queryFn: () => getSessionBehavior(sessionId), enabled, retry: false })
  const exports_  = useQuery({ queryKey: keys.exports(sessionId),   queryFn: () => getExports(sessionId),   enabled })

  const {
    ackMutation, resolveMutation, exportMutation, startLiveMutation, stopLiveMutation,
    evidenceMutation, verifyEvidenceMutation, validateEventsMutation, explainAlertMutation,
  } = useSessionDetailMutations(sessionId, qc)

  const loading = enabled && [session, insights, alerts, queue, events, evSummary, exports_].some(q => q.isPending)
  const error = [session, insights, alerts, queue, events, evSummary, exports_]
    .map(q => q.error)
    .find(Boolean) as Error | undefined

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
    createEvidence:   evidenceMutation.mutateAsync,
    generatingEvidence: evidenceMutation.isPending,
    verifyEvidence:   verifyEvidenceMutation.mutateAsync,
    verifyingEvidence: verifyEvidenceMutation.isPending,
    validateEvents:   validateEventsMutation.mutateAsync,
    validatingEvents: validateEventsMutation.isPending,
    eventValidation:  validateEventsMutation.data,
    explainAlert:     explainAlertMutation.mutateAsync,
  }
}
