import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { useGuestFlowStore } from '../store'
import { useEnroll } from '../hooks/useEnroll'

// Keyed by the reason code validate_selfie() sends back in the 422 detail
// (backend/app/cv/quality.py) — mapped to plain copy instead of showing the
// raw snake_case code to the guest.
const REJECTION_MESSAGES: Record<string, string> = {
  no_face_detected: "We couldn't find a face in that photo. Make sure your face is clearly visible and try again.",
  multiple_faces_detected: "We found more than one face in that photo. Make sure it's just you, then try again.",
  face_too_small: 'Your face was too small in the frame. Move closer and try again.',
  invalid_crop: 'That photo could not be processed. Try again with your face centered in the frame.',
  too_dark: 'That photo was too dark to use. Move somewhere brighter and try again.',
  too_bright: 'That photo was too bright to use. Reduce the lighting and try again.',
}
const DEFAULT_REJECTION_MESSAGE = "We couldn't use that photo. Try again with a clear, well-lit selfie."

interface EnrollStepProps {
  eventId: string
}

export function EnrollStep({ eventId }: EnrollStepProps) {
  const navigate = useNavigate()
  const selfieBlob = useGuestFlowStore((state) => state.selfieBlob)
  const consent = useGuestFlowStore((state) => state.consent)
  const setStep = useGuestFlowStore((state) => state.setStep)
  const reset = useGuestFlowStore((state) => state.reset)
  const enroll = useEnroll(eventId)

  // Guards against React re-running this effect (e.g. StrictMode's dev
  // double-invoke) and firing the enroll mutation, and its storage upload,
  // a second time.
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current || !selfieBlob) return
    startedRef.current = true
    enroll.mutate({ selfieBlob, consent })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selfieBlob, consent])

  useEffect(() => {
    if (enroll.isSuccess) {
      reset()
      navigate(`/events/${eventId}/mine`, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enroll.isSuccess])

  function handleRetry() {
    startedRef.current = false
    enroll.reset()
    setStep('capture')
  }

  if (enroll.isError) {
    const isRejection = enroll.error instanceof ApiError && enroll.error.status === 422
    const reasonCode = isRejection ? getDetail(enroll.error.body) : null
    const message = isRejection
      ? (reasonCode && REJECTION_MESSAGES[reasonCode]) || DEFAULT_REJECTION_MESSAGE
      : 'Something went wrong finding your photos. Try again.'

    return (
      <Card className="w-full max-w-sm">
        <AlertTriangle size={28} className="text-danger" aria-hidden="true" />
        <h1 className="mt-3 font-heading text-h1 text-text-primary">That selfie didn&apos;t work</h1>
        <p className="mt-2 text-body text-text-secondary">{message}</p>
        <Button className="mt-6" variant="primary" fullWidth onClick={handleRetry}>
          Try again
        </Button>
      </Card>
    )
  }

  return <Spinner center label="Finding your photos" />
}

function getDetail(body: unknown): string | null {
  return typeof body === 'object' && body !== null && typeof (body as { detail?: unknown }).detail === 'string'
    ? (body as { detail: string }).detail
    : null
}
