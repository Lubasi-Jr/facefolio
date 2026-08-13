import { api } from '@/lib/api'
import type { InvitationPublic } from '../types'

export function getInvitationPublic(token: string) {
  return api.get<InvitationPublic>(`/invitations/${token}`)
}

export function claimInvitation(token: string) {
  return api.post<void>(`/invitations/${token}/claim`)
}
