import { useQuery } from '@tanstack/react-query'
import { listEvents } from '../api/events'

export const eventsQueryKey = ['events'] as const

export function useEvents() {
  return useQuery({
    queryKey: eventsQueryKey,
    queryFn: listEvents,
  })
}
