/**
 * src/lib/queryClient.ts
 * -----------------------
 * Shared TanStack Query client. Single source of truth for caching/retry
 * defaults so every page gets deduped requests + background refetch for free.
 */

import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
