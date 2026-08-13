import { useQuery } from '@tanstack/react-query'
import { getInvitationPublic } from '../api/invitations'

export function useInvitation(token: string) {
  return useQuery({
    queryKey: ['invitations', token],
    queryFn: () => getInvitationPublic(token),
  })
}
