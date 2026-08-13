import { useMutation } from '@tanstack/react-query'
import { createInvitation } from '../api/invitations'

export function useCreateInvitation(eventId: string) {
  return useMutation({
    mutationFn: () => createInvitation(eventId),
  })
}
