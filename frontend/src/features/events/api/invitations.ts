import { api } from '@/lib/api'
import type { InvitationLink } from '../types'

export function createInvitation(eventId: string) {
  return api.post<InvitationLink>(`/events/${eventId}/invitations`, {})
}
