import { api } from '@/lib/api'
import type { ProcessingStatus } from '../types'

export function getProcessingStatus(eventId: string) {
  return api.get<ProcessingStatus>(`/events/${eventId}/processing-status`)
}
