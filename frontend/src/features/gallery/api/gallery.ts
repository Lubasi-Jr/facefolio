import { api } from '@/lib/api'
import type { GalleryResponse } from '../types'

export function getEventPhotos(eventId: string) {
  return api.get<GalleryResponse>(`/events/${eventId}/photos`)
}
