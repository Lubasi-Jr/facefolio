import { useMutation } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { claimInvitation } from '../api/invitations'

export function useClaimInvitation(token: string) {
  return useMutation({
    mutationFn: async () => {
      try {
        await claimInvitation(token)
      } catch (error) {
        // "Already a member" (409) means an earlier claim already went
        // through for this guest — treat it as success rather than an error.
        const alreadyMember =
          error instanceof ApiError &&
          error.status === 409 &&
          (error.body as { detail?: string } | null)?.detail === 'Already a member of this event'
        if (!alreadyMember) throw error
      }
    },
  })
}
