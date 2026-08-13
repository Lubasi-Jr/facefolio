// Mirrors backend/app/schemas/events.py

export type EventStatus = 'active' | 'expired' | 'purged'

export interface Event {
  id: string
  host_id: string
  name: string
  event_date: string | null
  expires_at: string
  status: EventStatus
  created_at: string
}

export interface CreateEventInput {
  name: string
  event_date?: string | null
  expires_at: string
}

// Mirrors backend/app/schemas/invitations.py — InvitationLinkRead

export type InvitationStatus = 'pending' | 'joined' | 'revoked'

export interface InvitationLink {
  id: string
  event_id: string
  status: InvitationStatus
  invite_link: string
}
