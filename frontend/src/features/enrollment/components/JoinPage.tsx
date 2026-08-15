import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, Ban } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useInvitation } from '../hooks/useInvitation'
import { useClaimInvitation } from '../hooks/useClaimInvitation'
import { useGuestFlowStore } from '../store'
import { ConsentStep } from './ConsentStep'
import { CaptureStep } from './CaptureStep'
import { EnrollStep } from './EnrollStep'

export function JoinPage() {
  const { token } = useParams<{ token: string }>()
  const { session, signInAnonymously } = useAuth()
  const { data: invitation, isPending, isError } = useInvitation(token!)
  const claim = useClaimInvitation(token!)
  const guestStep = useGuestFlowStore((state) => state.step)
  const [joinError, setJoinError] = useState('')

  async function handleJoin() {
    setJoinError('')
    try {
      // Anonymous sign-in gives us the JWT the claim call needs; skip it if
      // the guest already has a session (e.g. they reloaded this page).
      if (!session) {
        await signInAnonymously()
      }
      await claim.mutateAsync()
    } catch (error) {
      setJoinError(error instanceof Error ? error.message : 'Something went wrong. Try again.')
    }
  }

  if (isPending) {
    return <Spinner center label="Loading invite" />
  }

  if (isError) {
    return (
      <EmptyState
        icon={<AlertTriangle size={32} />}
        title="Invite not found"
        description="This link may be mistyped or no longer exists."
      />
    )
  }

  if (invitation.join_status === 'expired') {
    return (
      <EmptyState
        icon={<AlertTriangle size={32} />}
        title="This event has ended"
        description={`${invitation.event_name} is no longer accepting new guests.`}
      />
    )
  }

  if (invitation.join_status === 'revoked') {
    return (
      <EmptyState
        icon={<Ban size={32} />}
        title="Invite no longer valid"
        description="This invite link has been revoked by the host."
      />
    )
  }

  if (claim.isSuccess) {
    if (guestStep === 'capture') {
      return <CaptureStep />
    }
    if (guestStep === 'enroll') {
      return <EnrollStep eventId={invitation.event_id} />
    }
    return <ConsentStep eventName={invitation.event_name} />
  }

  return (
    <Card className="w-full max-w-sm">
      <h1 className="font-heading text-h1 text-text-primary">{invitation.event_name}</h1>
      <p className="mt-2 text-body text-text-secondary">
        Join to find your photos from this event.
      </p>

      {joinError && (
        <div className="mt-6 rounded-interactive bg-danger-bg px-4 py-3 text-small text-danger">
          {joinError}
        </div>
      )}

      <Button
        className="mt-8"
        variant="primary"
        fullWidth
        isLoading={claim.isPending}
        onClick={handleJoin}
      >
        Join event
      </Button>
    </Card>
  )
}
