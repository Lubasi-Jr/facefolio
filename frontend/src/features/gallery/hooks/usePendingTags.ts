import { useQuery } from '@tanstack/react-query'
import { getPendingTags } from '../api/tags'

export function pendingTagsQueryKey(eventId: string) {
  return ['pending-tags', eventId]
}

export function usePendingTags(eventId: string, enabled = true) {
  return useQuery({
    queryKey: pendingTagsQueryKey(eventId),
    queryFn: () => getPendingTags(eventId),
    enabled,
  })
}
