import { api } from '@/lib/api'
import type { CreateEventInput, Event } from '../types'

export function listEvents() {
  return api.get<Event[]>('/events')
}

export function createEvent(input: CreateEventInput) {
  return api.post<Event>('/events', input)
}

export function getEvent(id: string) {
  return api.get<Event>(`/events/${id}`)
}

export function deleteEvent(id: string) {
  return api.delete<void>(`/events/${id}`)
}
