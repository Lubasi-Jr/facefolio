import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createEvent } from '../api/events'
import { eventsQueryKey } from './useEvents'

export function useCreateEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createEvent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: eventsQueryKey })
    },
  })
}
