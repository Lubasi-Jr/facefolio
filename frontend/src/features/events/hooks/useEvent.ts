import { useQuery } from '@tanstack/react-query'
import { getEvent } from '../api/events'

export function useEvent(id: string) {
  return useQuery({
    queryKey: ['events', id],
    queryFn: () => getEvent(id),
  })
}
