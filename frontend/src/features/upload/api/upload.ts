import { api } from '@/lib/api'
import type { PhotoConfirmResponse, PreparePhotoItem, PreparePhotosResponse } from '../types'

export function preparePhotos(eventId: string, photos: PreparePhotoItem[]) {
  return api.post<PreparePhotosResponse>(`/events/${eventId}/photos/prepare`, { photos })
}

export function confirmPhoto(eventId: string, photoId: string) {
  return api.post<PhotoConfirmResponse>(`/events/${eventId}/photos/${photoId}/confirm`)
}
