import { useQuery } from '@tanstack/react-query'
import { isProcessingSettled, useProcessingStatus } from '@/features/upload'
import { getEventPhotos } from '../api/gallery'

const POLL_INTERVAL_MS = 3000

// Shares the same processing-status poll the uploader watches (same query
// key, so this doesn't add a second network call) and stops refetching
// thumbnails at exactly the moment that poll considers processing done.
export function useEventPhotos(eventId: string) {
  const { data: processingStatus } = useProcessingStatus(eventId)
  const isDone = !!processingStatus && isProcessingSettled(processingStatus)

  return useQuery({
    queryKey: ['event-photos', eventId],
    queryFn: () => getEventPhotos(eventId),
    refetchInterval: isDone ? false : POLL_INTERVAL_MS,
  })
}
