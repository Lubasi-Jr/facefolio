import { useQuery } from '@tanstack/react-query'
import { getProcessingStatus } from '../api/processing'
import type { ProcessingStatus } from '../types'

const POLL_INTERVAL_MS = 3000

// Exported so other features polling the same event (e.g. the host gallery)
// can agree on exactly what "processing is done" means.
export function isProcessingSettled(status: ProcessingStatus) {
  const total =
    status.awaiting_upload + status.queued + status.processing + status.processed + status.failed
  return total > 0 && status.processed + status.failed === total
}

export function useProcessingStatus(eventId: string) {
  return useQuery({
    queryKey: ['processing-status', eventId],
    queryFn: () => getProcessingStatus(eventId),
    // Poll while anything is still awaiting upload/queued/processing; stop
    // the moment every photo has landed in a terminal state (processed or
    // failed) so the page isn't hammering the backend once there's nothing
    // left to watch.
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || isProcessingSettled(data)) return false
      return POLL_INTERVAL_MS
    },
  })
}
