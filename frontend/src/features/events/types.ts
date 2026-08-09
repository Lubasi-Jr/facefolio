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
