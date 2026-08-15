import { useEffect, useRef, useState } from 'react'
import type React from 'react'
import { Download, X } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import type { GalleryPhoto } from '../types'

interface LightboxProps {
  photo: GalleryPhoto | null
  onClose: () => void
}

export function Lightbox({ photo, onClose }: LightboxProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  // Same pattern as CreateEventDialog: the `photo` prop drives the native
  // dialog's imperative showModal()/close() API rather than controlling it
  // through React state directly.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (photo && !dialog.open) {
      dialog.showModal()
    } else if (!photo && dialog.open) {
      dialog.close()
    }
  }, [photo])

  function handleBackdropClick(event: React.MouseEvent<HTMLDialogElement>) {
    const rect = dialogRef.current?.getBoundingClientRect()
    if (!rect) return
    const inBounds =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom
    if (!inBounds) onClose()
  }

  async function handleDownload() {
    if (!photo || isDownloading) return
    setIsDownloading(true)
    try {
      // Fetch the signed URL into a blob rather than linking to it directly:
      // an <a download> on a cross-origin URL is frequently ignored by the
      // browser (it just navigates), but a blob: URL is same-origin and
      // download always works.
      const response = await fetch(photo.web_url)
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `${photo.photo_id}.jpg`
      link.click()
      URL.revokeObjectURL(blobUrl)
    } catch {
      // Downloading is a nice-to-have on top of viewing the photo; a failed
      // fetch here shouldn't block or error out the lightbox itself.
    } finally {
      setIsDownloading(false)
    }
  }

  if (!photo) {
    return <dialog ref={dialogRef} onClose={onClose} className="hidden" />
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={handleBackdropClick}
      className="w-full max-w-3xl rounded-container border border-border bg-surface p-4"
    >
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloading}
          aria-label="Download photo"
          className="flex items-center gap-2 rounded-interactive px-3 py-2 text-small font-medium text-text-secondary hover:bg-background disabled:text-text-disabled"
        >
          {isDownloading ? <Spinner size="sm" /> : <Download size={18} />}
          Download
        </button>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="text-text-secondary hover:text-text-primary"
        >
          <X size={20} />
        </button>
      </div>

      <div className="mt-2 overflow-hidden rounded-container bg-surface-muted">
        <img src={photo.web_url} alt="Event photo" className="max-h-[70vh] w-full object-contain" />
      </div>
    </dialog>
  )
}
