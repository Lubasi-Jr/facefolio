import { ScanFace, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useGuestFlowStore } from '../store'

interface ConsentStepProps {
  eventName: string
}

// Gate before the camera opens. Pressing "I agree" is itself the consent
// action — there's no separate checkbox to pre-check or auto-advance past.
// The button is not autoFocus'd, so it can't be triggered by an accidental
// keypress before the guest has read the explanation.
export function ConsentStep({ eventName }: ConsentStepProps) {
  const setConsent = useGuestFlowStore((state) => state.setConsent)
  const setStep = useGuestFlowStore((state) => state.setStep)

  function handleAgree() {
    setConsent(true)
    setStep('capture')
  }

  return (
    <Card className="w-full max-w-sm">
      <ScanFace size={28} className="text-primary" aria-hidden="true" />
      <h1 className="mt-3 font-heading text-h1 text-text-primary">Before you take a selfie</h1>
      <p className="mt-2 text-body text-text-secondary">
        To find your photos from {eventName}, FaceFolio uses facial recognition: we
        scan the selfie you take and compare it against every face detected in this
        event&apos;s photos.
      </p>

      <ul className="mt-6 flex flex-col gap-4">
        <li className="flex items-start gap-3">
          <ScanFace size={20} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden="true" />
          <span className="text-small text-text-secondary">
            This is facial recognition. Your selfie is analyzed as a biometric face
            match, not just stored as a picture.
          </span>
        </li>
        <li className="flex items-start gap-3">
          <Trash2 size={20} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden="true" />
          <span className="text-small text-text-secondary">
            Your selfie and face data are permanently deleted when this event expires.
          </span>
        </li>
      </ul>

      <Button className="mt-8" variant="primary" fullWidth onClick={handleAgree}>
        I agree
      </Button>
    </Card>
  )
}
