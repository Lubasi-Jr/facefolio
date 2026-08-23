import { api } from '@/lib/api'
import type { PendingTagsResponse, TagReviewResponse } from '../types'

export function getPendingTags(eventId: string) {
  return api.get<PendingTagsResponse>(`/events/${eventId}/pending-tags/mine`)
}

export function confirmTag(photoId: string) {
  return api.post<TagReviewResponse>(`/tags/${photoId}/confirm`)
}

export function rejectTag(photoId: string) {
  return api.post<TagReviewResponse>(`/tags/${photoId}/reject`)
}
