/**
 * src/store/appStore.ts
 * ----------------------
 * Global state using Zustand.
 * Keeps all shared data in one place — components read from here, not from
 * local state wherever multiple components need the same data.
 */

import { create } from 'zustand'
import type {
  Session, GlobalMetrics, Insight, Alert,
  AlertSummary, ReviewItem, QueueSummary,
} from '../services/api'

interface AppState {
  // ── Data ──────────────────────────────────────────────────────────────────
  sessions:     Session[]
  metrics:      GlobalMetrics | null
  insights:     Insight[]
  alerts:       Alert[]
  alertSummary: AlertSummary | null
  reviewItems:  ReviewItem[]
  queueSummary: QueueSummary | null

  // ── Loading states ─────────────────────────────────────────────────────────
  loading: {
    sessions:    boolean
    metrics:     boolean
    insights:    boolean
    alerts:      boolean
    reviewItems: boolean
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  error: string | null

  // ── Setters ────────────────────────────────────────────────────────────────
  setSessions:     (sessions: Session[])         => void
  setMetrics:      (metrics: GlobalMetrics)      => void
  setInsights:     (insights: Insight[])         => void
  setAlerts:       (alerts: Alert[])             => void
  setAlertSummary: (summary: AlertSummary)       => void
  setReviewItems:  (items: ReviewItem[])         => void
  setQueueSummary: (summary: QueueSummary)       => void
  setLoading:      (key: keyof AppState['loading'], value: boolean) => void
  setError:        (error: string | null)        => void
}

export const useAppStore = create<AppState>((set) => ({
  sessions:     [],
  metrics:      null,
  insights:     [],
  alerts:       [],
  alertSummary: null,
  reviewItems:  [],
  queueSummary: null,

  loading: {
    sessions:    false,
    metrics:     false,
    insights:    false,
    alerts:      false,
    reviewItems: false,
  },

  error: null,

  setSessions:     (sessions)     => set({ sessions }),
  setMetrics:      (metrics)      => set({ metrics }),
  setInsights:     (insights)     => set({ insights }),
  setAlerts:       (alerts)       => set({ alerts }),
  setAlertSummary: (alertSummary) => set({ alertSummary }),
  setReviewItems:  (reviewItems)  => set({ reviewItems }),
  setQueueSummary: (queueSummary) => set({ queueSummary }),
  setLoading: (key, value) =>
    set((s) => ({ loading: { ...s.loading, [key]: value } })),
  setError: (error) => set({ error }),
}))
