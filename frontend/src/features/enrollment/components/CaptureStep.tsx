import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Camera, ImageUp, RotateCcw } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { useGuestFlowStore } from '../store'

type CameraState = 'requesting' | 'ready' | 'unavailable'

export function CaptureStep() {
  const setSelfieBlob = useGuestFlowStore((state) => state.setSelfieBlob)
  const setStep = useGuestFlowStore((state) => state.setStep)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Starts at 'requesting' by default for the initial mount; bumped by
  // handleRetake to re-run the effect below for a second attempt.
  const [cameraState, setCameraState] = useState<CameraState>('requesting')
  const [cameraMessage, setCameraMessage] = useState('')
  const [cameraAttempt, setCameraAttempt] = useState(0)
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  function stopStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  // Requests the camera whenever cameraAttempt changes. State updates only
  // happen inside the promise callbacks (after the request resolves), never
  // synchronously in the effect body itself, so re-mounts/retakes can't
  // trigger a cascading render.
  useEffect(() => {
    let cancelled = false

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'user' }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) videoRef.current.srcObject = stream
        setCameraState('ready')
      })
      .catch((error) => {
        if (cancelled) return
        const name = error instanceof DOMException ? error.name : ''
        setCameraMessage(
          name === 'NotAllowedError' || name === 'PermissionDeniedError'
            ? 'Camera access was denied. You can still continue by choosing a photo instead.'
            : "We couldn't reach a camera on this device. Choose a photo instead."
        )
        setCameraState('unavailable')
      })

    return () => {
      cancelled = true
      stopStream()
    }
  }, [cameraAttempt])

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  function showPreview(blob: Blob) {
    stopStream()
    setPreviewUrl(URL.createObjectURL(blob))
    setCapturedBlob(blob)
  }

  function handleCapture() {
    const video = videoRef.current
    if (!video) return

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // The live preview is mirrored (CSS scale-x-[-1]) so it feels like a
    // mirror, not a reversed camera feed. Mirror the drawn frame too, so the
    // captured photo matches what the guest actually saw and confirmed.
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(
      (blob) => {
        if (blob) showPreview(blob)
      },
      'image/jpeg',
      0.92
    )
  }

  function handleFileChosen(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    showPreview(file)
  }

  function handleRetake() {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setCapturedBlob(null)
    if (cameraState === 'ready') {
      setCameraState('requesting')
      setCameraAttempt((attempt) => attempt + 1)
    }
  }

  function handleUsePhoto() {
    if (!capturedBlob) return
    setSelfieBlob(capturedBlob)
    setStep('enroll')
  }

  const openFilePicker = () => fileInputRef.current?.click()

  const hiddenFileInput = (
    <input
      ref={fileInputRef}
      type="file"
      accept="image/*"
      className="hidden"
      onChange={handleFileChosen}
    />
  )

  if (capturedBlob && previewUrl) {
    return (
      <Card className="w-full max-w-sm">
        <h1 className="font-heading text-h1 text-text-primary">Use this photo?</h1>
        <p className="mt-2 text-body text-text-secondary">
          Make sure your face is clear and well-lit before continuing.
        </p>

        <div className="mt-6 aspect-square w-full overflow-hidden rounded-container bg-surface-muted">
          <img src={previewUrl} alt="Your selfie preview" className="h-full w-full object-cover" />
        </div>

        <div className="mt-6 flex gap-3">
          <Button
            variant="secondary"
            fullWidth
            leftIcon={<RotateCcw size={18} />}
            onClick={handleRetake}
          >
            Retake
          </Button>
          <Button variant="primary" fullWidth onClick={handleUsePhoto}>
            Use this photo
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-sm">
      <h1 className="font-heading text-h1 text-text-primary">Take a selfie</h1>
      <p className="mt-2 text-body text-text-secondary">
        Center your face in the circle, in good light, and hold still.
      </p>

      <div className="relative mt-6 aspect-square w-full overflow-hidden rounded-container bg-surface-muted">
        {cameraState === 'requesting' && <Spinner center label="Requesting camera access" />}

        {cameraState === 'unavailable' && (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
            <AlertTriangle size={28} className="text-warning" aria-hidden="true" />
            <p className="text-small text-text-secondary">{cameraMessage}</p>
          </div>
        )}

        {cameraState === 'ready' && (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="h-full w-full scale-x-[-1] object-cover"
            />
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div
                className="aspect-square w-[70%] rounded-full border-2 border-surface"
                style={{ boxShadow: '0 0 0 9999px var(--color-scrim)' }}
              />
            </div>
          </>
        )}
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {cameraState === 'ready' && (
          <Button variant="primary" fullWidth leftIcon={<Camera size={18} />} onClick={handleCapture}>
            Capture
          </Button>
        )}
        <Button
          variant={cameraState === 'ready' ? 'ghost' : 'primary'}
          fullWidth
          leftIcon={<ImageUp size={18} />}
          onClick={openFilePicker}
        >
          Choose a photo instead
        </Button>
      </div>

      {hiddenFileInput}
    </Card>
  )
}
