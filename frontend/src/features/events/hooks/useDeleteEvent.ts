import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteEvent } from '../api/events'
import { eventsQueryKey } from './useEvents'

export function useDeleteEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteEvent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: eventsQueryKey })
    },
  })
}
