// Mirrors backend/app/schemas/invitations.py — InvitationPublicRead
export type JoinStatus = 'joinable' | 'revoked' | 'expired'

export interface InvitationPublic {
  event_name: string
  join_status: JoinStatus
}
