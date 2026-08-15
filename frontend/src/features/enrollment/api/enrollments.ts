import { api } from '@/lib/api'
import type { EnrollRequest, EnrollResponse, PrepareEnrollmentResponse } from '../types'

export function prepareEnrollment(eventId: string) {
  return api.post<PrepareEnrollmentResponse>(`/events/${eventId}/enrollments/prepare`)
}

export function enroll(eventId: string, body: EnrollRequest) {
  return api.post<EnrollResponse>(`/events/${eventId}/enroll`, body)
}
