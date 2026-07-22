/**
 * src/services/api.ts - SessionGuard v1.1
 * Single source for all API calls. 0 duplicates.
 */
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const API_VERSION = '/api/v1'

const client = axios.create({ baseURL: BASE, timeout: 10_000 })

client.interceptors.request.use(cfg => {
  const token = sessionStorage.getItem('sg_access_token')
  if (token && cfg.headers) cfg.headers.Authorization = `Bearer ${token}`
  if (cfg.data instanceof FormData) {
    delete cfg.headers['Content-Type']
  } else {
    cfg.headers['Content-Type'] = 'application/json'
  }
  
  // Add API version prefix to all requests except health endpoints
  if (cfg.url && !cfg.url.startsWith('/health')) {
    cfg.url = `${API_VERSION}${cfg.url}`
  }
  
  return cfg
})

export { client }

// ── Types ─────────────────────────────────────────────────────────────────────
export interface Session {
  id: number; name: string; game_name: string; platform: string
  date: string; duration_minutes: number; start_balance: number
  end_balance: number; total_bets: number; total_wins: number
  net_result: number; rtp: number; spins: number; biggest_win: number
  biggest_loss: number; losing_streak: number; status: string; notes: string
}
export interface GlobalMetrics {
  total_sessions: number; total_net: number; avg_rtp: number
  avg_net: number; total_wagered: number; flagged_sessions: number; total_spins: number
}
// Insight — game_name and session_id are returned by the API
export interface Insight {
  id: number; session_id: number; text: string; severity: string
  created_at: string; game_name?: string
}
// Alert — session_name is returned by the API alongside the alert
export interface Alert {
  id: number; session_id: number; severity: string; message: string
  acknowledged: number; created_at: string; session_name?: string
}
export interface AlertSummary { total: number; critical: number; warning: number; info: number; unacknowledged: number }
// ReviewItem — confidence_score and game_name come from joined API response
export interface ReviewItem {
  id: number; session_id: number; event_id: number
  confidence: number; confidence_score?: number
  reason: string; status: string; correction: string | null
  game_name?: string
}
// QueueSummary — corrected is an optional field some backend versions include
export interface QueueSummary { pending: number; accepted: number; rejected: number; total: number; corrected?: number }
export interface SessionEvent { id: number; session_id: number; timestamp: string; event_type: string; bet_amount: number; win_amount: number; balance_after: number; confidence_score: number }
export interface EventSummary { total: number; winning: number; avg_bet: number; biggest_win: number; net_over_time: Array<{ spin: number; cumulative: number; balance: number }> }
export interface BehaviorResult { session_id: number; status: string; risk_level: string; risk_score: number; findings: string[]; patterns: Record<string, any> }
// LiveRun — extended with fields used by LiveMonitor
export interface LiveRun {
  id: number; session_id: number; status: string; mode: string
  event_count: number; event_index: number
  tick_interval: number; started_at?: string; stopped_at?: string
}
export interface LiveEvent { id: number; run_id: number; event_type: string; payload: Record<string, any>; created_at: string }
export interface AiAnalysis { session_id: number; source: string; ai_available: boolean; headline: string; risk_level: string; discipline_score: number; one_line_verdict: string; insights: any[]; behaviour_summary: string }
export interface AiStatus { available: boolean; has_library: boolean; has_api_key: boolean; model: string; message: string; install_cmd: string | null; key_env_var: string; console_url: string }
// CompareResult — returned by /compare endpoint
export interface CompareResult {
  session_ids: number[]
  sessions: Session[]
  metric_rows: Array<{ metric: string; values: number[]; winner_idx: number }>
  narrative?: string
  saved_id?: number
}
// NetOverTime / RtpBucket — used by Dashboard charts
export interface NetOverTime { date: string; cumulative_net: number }
export interface RtpBucket   { bucket: string; count: number }

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth         = () => client.get('/health').then(r => r.data)
export const getHealthDetailed = () => client.get('/health/detailed').then(r => r.data)

// ── Sessions ──────────────────────────────────────────────────────────────────
export const getSessions    = (params: any = {}) => client.get('/sessions', { params }).then(r => r.data)
export const getSession     = (id: number) => client.get(`/sessions/${id}`).then(r => r.data)
export const createSession  = (data: any) => client.post('/sessions', data).then(r => r.data)
export const updateSession  = (id: number, data: any) => client.patch(`/sessions/${id}`, data).then(r => r.data)
export const deleteSession  = (id: number) => client.delete(`/sessions/${id}`).then(r => r.data)
export const getSessionHealth  = (id: number) => client.get(`/sessions/${id}/health`).then(r => r.data)
export const getSessionDrift   = (id: number, project_n = 20) => client.get(`/sessions/${id}/drift`, { params: { project_n } }).then(r => r.data)
export const getEarlyWarnings  = (id: number) => client.get(`/sessions/${id}/warnings`).then(r => r.data)
export const getSessionNotes   = (id: number) => client.get(`/sessions/${id}/notes`).then(r => r.data)
export const addSessionNote    = (id: number, note: string) => client.post(`/sessions/${id}/notes`, { note }).then(r => r.data)
export const getSessionOcrResults = (id: number) => client.get(`/sessions/${id}/ocr-results`).then(r => r.data)
export const createEvidence    = (id: number) => client.post(`/sessions/${id}/evidence`).then(r => r.data)
export const getEvidenceDownload = (sid: number, eid: number) => `${BASE}${API_VERSION}/sessions/${sid}/evidence/${eid}/download`
export const getSessionTags    = (id: number) => client.get(`/sessions/${id}/tags`).then(r => r.data)
export const addSessionTag     = (id: number, tag: string) => client.post(`/sessions/${id}/tags`, { tag }).then(r => r.data)
export const removeSessionTag  = (id: number, tag: string) => client.delete(`/sessions/${id}/tags/${tag}`).then(r => r.data)

// ── Metrics ───────────────────────────────────────────────────────────────────
export const getGlobalMetrics    = () => client.get('/metrics').then(r => r.data)
export const getRtpDistribution  = () => client.get('/metrics/rtp-distribution').then(r => r.data)
export const getNetOverTime      = () => client.get('/metrics/net-over-time').then(r => r.data)
export const getPerformanceByGame= () => client.get('/metrics/by-game').then(r => r.data)
export const getSessionMetrics   = (id: number) => client.get(`/metrics/session/${id}`).then(r => r.data)

// ── Dashboard (aggregated) ────────────────────────────────────────────────────
export const getDashboardSummary = () => client.get('/dashboard/summary').then(r => r.data)

// ── Insights ──────────────────────────────────────────────────────────────────
export const getInsights         = (params: any = {}) => client.get('/insights', { params }).then(r => r.data)
export const regenerateInsights  = (id: number) => client.post(`/insights/${id}/regenerate`).then(r => r.data)

// ── Alerts ────────────────────────────────────────────────────────────────────
export const getAlerts           = (params: any = {}) => client.get('/alerts', { params }).then(r => r.data)
export const getAlertsSummary    = () => client.get('/alerts/summary').then(r => r.data)
export const getAlertSummary     = () => client.get('/alerts/summary').then(r => r.data)
export const acknowledgeAlert    = (id: number) => client.patch(`/alerts/${id}/acknowledge`).then(r => r.data)

// ── Review Queue ──────────────────────────────────────────────────────────────
export const getReviewQueue      = (params: any = {}) => client.get('/review-queue', { params }).then(r => r.data)
export const getReviewSummary    = () => client.get('/review-queue/summary').then(r => r.data)
export const getQueueSummary     = () => client.get('/review-queue/summary').then(r => r.data)
export const resolveReviewItem   = (id: number, data: any) => client.patch(`/review-queue/${id}/resolve`, data).then(r => r.data)

// ── Upload ────────────────────────────────────────────────────────────────────
export const uploadFile = (file: File, session_id?: number) => {
  const fd = new FormData()
  fd.append('file', file)
  if (session_id != null) fd.append('session_id', String(session_id))
  return client.post('/upload', fd).then(r => r.data)
}
export const getUploads          = () => client.get('/upload').then(r => r.data)
export const getCsvTemplate      = (type = 'spin') => `${BASE}${API_VERSION}/upload/template/${type}`

// ── Exports ───────────────────────────────────────────────────────────────────
export const createExport        = (format: string, session_id?: number) => client.post('/exports', { format, session_id }).then(r => r.data)
export const getExports          = (session_id?: number) => client.get('/exports', { params: { session_id } }).then(r => r.data)
export const getExportDownloadUrl= (id: number) => `${BASE}${API_VERSION}/exports/${id}/download`

// ── Compare ───────────────────────────────────────────────────────────────────
export const compareSessions     = (session_ids: number[]) => client.post('/compare', { session_ids }).then(r => r.data)

// ── Profiles ──────────────────────────────────────────────────────────────────
export const getProfiles         = () => client.get('/profiles').then(r => r.data)
export const createProfile       = (data: any) => client.post('/profiles', data).then(r => r.data)
export const updateProfile       = (id: number, data: any) => client.patch(`/profiles/${id}`, data).then(r => r.data)
export const deleteProfile       = (id: number) => client.delete(`/profiles/${id}`).then(r => r.data)

// ── Status ────────────────────────────────────────────────────────────────────
export const getVideoStatus      = () => client.get('/video-status').then(r => r.data)
export const getOcrStatus        = () => client.get('/ocr-status').then(r => r.data)

// ── Events ────────────────────────────────────────────────────────────────────
export const getEvents           = (params: any = {}) => client.get('/events', { params }).then(r => r.data)
export const getEventsSummary    = (session_id: number) => client.get('/events/summary', { params: { session_id } }).then(r => r.data)
export const getSessionEvents    = (id: number) => client.get('/events', { params: { session_id: id } }).then(r => r.data)

// ── Behavior ──────────────────────────────────────────────────────────────────
export const getSessionBehavior  = (id: number) => client.get(`/behavior/session/${id}`).then(r => r.data)
export const getGlobalBehavior   = () => client.get('/behavior/global').then(r => r.data)

// ── Live ──────────────────────────────────────────────────────────────────────
export const startLiveRun  = (data: { session_id: number; mode?: string; tick_interval?: number }) => client.post('/live/start', data).then(r => r.data)
export const getLiveRun    = (id: number) => client.get(`/live/${id}`).then(r => r.data)
export const pauseLiveRun  = (id: number) => client.post(`/live/${id}/pause`).then(r => r.data)
export const resumeLiveRun = (id: number) => client.post(`/live/${id}/resume`).then(r => r.data)
export const stopLiveRun   = (id: number) => client.post(`/live/${id}/stop`).then(r => r.data)
export const getLiveEvents = (id: number, since_id = 0) => client.get(`/live/${id}/events`, { params: { since_id } }).then(r => r.data)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login    = (email: string, password: string) => client.post('/auth/login', { email, password }).then(r => r.data)
export const signup   = (data: any) => client.post('/auth/signup', data).then(r => r.data)
export const getMe    = () => client.get('/auth/me').then(r => r.data)
export const authLogout = () => client.post('/auth/logout').then(r => r.data)

// ── Projects ──────────────────────────────────────────────────────────────────
export const getProjects   = () => client.get('/projects').then(r => r.data)
export const createProject = (data: any) => client.post('/projects', data).then(r => r.data)
export const deleteProject = (id: number) => client.delete(`/projects/${id}`).then(r => r.data)

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const getJobs   = () => client.get('/jobs').then(r => r.data)
export const getJob    = (id: number) => client.get(`/jobs/${id}`).then(r => r.data)
export const enqueueJob= (data: any) => client.post('/jobs', data).then(r => r.data)
export const cancelJob = (id: number) => client.post(`/jobs/${id}/cancel`).then(r => r.data)

// ── Trends ────────────────────────────────────────────────────────────────────
export const getRollingTrends  = (last_n = 10) => client.get('/trends/rolling', { params: { last_n } }).then(r => r.data)
export const getSessionStreaks = () => client.get('/trends/streaks').then(r => r.data)
export const getPatternMemory  = (last_n = 20) => client.get('/trends/pattern-memory', { params: { last_n } }).then(r => r.data)

// ── Search + Tags ─────────────────────────────────────────────────────────────
export const globalSearch = (q: string, limit = 20) => client.get('/search', { params: { q, limit } }).then(r => r.data)
export const getAllTags   = () => client.get('/tags/all').then(r => r.data)

// ── V12 Intelligence ──────────────────────────────────────────────────────────
export const buildClusters     = (threshold = 0.88) => client.post('/intelligence/clusters/build', null, { params: { threshold } }).then(r => r.data)
export const getClusters       = () => client.get('/intelligence/clusters').then(r => r.data)
export const getSessionCluster = (id: number) => client.get(`/intelligence/clusters/session/${id}`).then(r => r.data)
export const getPeerBenchmark  = (id: number) => client.get(`/intelligence/benchmark/${id}`).then(r => r.data)
export const getDatasetSummary = () => client.get('/intelligence/dataset-summary').then(r => r.data)
export const getAnomalies      = () => client.get('/intelligence/anomalies').then(r => r.data)

// ── V13 AI ────────────────────────────────────────────────────────────────────
export const getAiStatus           = () => client.get('/intelligence/ai/status').then(r => r.data)
export const getAiNarrative        = (id: number, force = false) => client.get(`/intelligence/ai/session/${id}`, { params: { force_refresh: force } }).then(r => r.data)
export const runAiAnalysis         = (id: number, force = false) => client.get(`/intelligence/ai/session/${id}`, { params: { force_refresh: force } }).then(r => r.data)
export const getCachedAiAnalysis   = (id: number) => client.get(`/intelligence/ai/session/${id}`).then(r => r.data)
export const getAiComparison       = (session_ids: number[]) => client.post('/intelligence/ai/compare', { session_ids }).then(r => r.data)
export const getAiReviewSuggestion = (id: number) => client.get(`/intelligence/ai/review/${id}`).then(r => r.data)

// ── System + Recorder ─────────────────────────────────────────────────────────
export const getSystemConfig   = () => client.get('/system-config').then(r => r.data)
export const updateSystemConfig= (key: string, value: any) => client.patch('/system-config', { key, value }).then(r => r.data)
export const getDbBackupUrl    = () => `${BASE}${API_VERSION}/data-export/backup`
export const getRecorderStatus = () => client.get('/recorder/status').then(r => r.data)
export const startRecording    = (session_id?: number, fps = 30) => client.post('/recorder/start', { session_id, fps }).then(r => r.data)
export const stopRecording     = () => client.post('/recorder/stop').then(r => r.data)
