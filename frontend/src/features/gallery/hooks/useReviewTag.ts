import { useMutation, useQueryClient } from '@tanstack/react-query'
import { confirmTag, rejectTag } from '../api/tags'
import { pendingTagsQueryKey } from './usePendingTags'
import type { PendingTagsResponse, TagReviewDecision } from '../types'

interface ReviewTagInput {
  photoId: string
  decision: TagReviewDecision
}

export function useReviewTag(eventId: string) {
  const queryClient = useQueryClient()
  const queryKey = pendingTagsQueryKey(eventId)

  return useMutation({
    mutationFn: ({ photoId, decision }: ReviewTagInput) =>
      decision === 'confirm' ? confirmTag(photoId) : rejectTag(photoId),

    // Optimistic: drop the card from the pending list immediately rather
    // than waiting on the round trip, then reconcile in onError/onSettled.
    onMutate: async ({ photoId }) => {
      await queryClient.cancelQueries({ queryKey })
      const previous = queryClient.getQueryData<PendingTagsResponse>(queryKey)

      queryClient.setQueryData<PendingTagsResponse>(queryKey, (current) =>
        current ? { tags: current.tags.filter((tag) => tag.photo_id !== photoId) } : current
      )

      return { previous }
    },

    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous)
      }
    },

    onSettled: (_data, _error, { decision }) => {
      queryClient.invalidateQueries({ queryKey })
      // A confirmed tag now belongs in "Photos of you" — same query key
      // useMyPhotos uses, so this picks it up without a second endpoint.
      if (decision === 'confirm') {
        queryClient.invalidateQueries({ queryKey: ['my-photos', eventId] })
      }
    },
  })
}
