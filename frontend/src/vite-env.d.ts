/// <reference types="vite/client" />

// Extend missing fields across interfaces globally
declare module '../services/api' {
  interface GlobalMetrics {
    all_time_biggest_win?: number
    worst_streak?: number
    flagged_count?: number
  }
  interface Insight { game_name?: string }
  interface Alert { session_name?: string }
  interface ReviewItem {
    confidence_score?: number
    game_name?: string
    session_name?: string
    bet_amount?: number
    win_amount?: number
    event_timestamp?: string
    corrected?: number
  }
  interface SessionEvent { spin_number?: number; source?: string }
  interface EventSummary {
    win_rate_pct?: number
    total_events?: number
    winning_spins?: number
    losing_spins?: number
    low_conf_count?: number
  }
  interface BehaviorResult { summary?: string }
  interface LiveRun { event_index?: number; tick_interval?: number; started_at?: string }
  interface AiAnalysis { model?: string; generated_at?: string; error?: string; notable_moments?: string[]; cost_per_session?: number }
  interface AiStatus { cost_per_session?: number }
  interface QueueSummary { corrected?: number }
}
