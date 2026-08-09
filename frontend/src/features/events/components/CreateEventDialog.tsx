import { useEffect, useRef, useState } from 'react'
import type React from 'react'
import { X } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { useCreateEvent } from '../hooks/useCreateEvent'

interface CreateEventDialogProps {
  open: boolean
  onClose: () => void
}

export function CreateEventDialog({ open, onClose }: CreateEventDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const createEvent = useCreateEvent()

  // The `open` prop drives the imperative showModal()/close() API — a native
  // dialog isn't controlled by React state directly.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  function resetForm() {
    setName('')
    setEventDate('')
    setExpiresAt('')
    setErrorMessage('')
    createEvent.reset()
  }

  // Fires on Esc, on the native backdrop click check below, and on our own
  // close()/Cancel calls — the single place that syncs back to the parent.
  function handleClose() {
    resetForm()
    onClose()
  }

  // Clicking the ::backdrop reports the <dialog> element itself as the
  // click target, but so does clicking its own padding — so check the
  // click coordinates against the dialog's box instead of target equality.
  function handleBackdropClick(event: React.MouseEvent<HTMLDialogElement>) {
    const rect = dialogRef.current?.getBoundingClientRect()
    if (!rect) return
    const inBounds =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom
    if (!inBounds) {
      handleClose()
    }
  }

  const handleSubmit: React.SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    setErrorMessage('')
    try {
      await createEvent.mutateAsync({
        name,
        event_date: eventDate || null,
        expires_at: new Date(expiresAt).toISOString(),
      })
      resetForm()
      onClose()
    } catch (error) {
      if (error instanceof ApiError && isDetailMessage(error.body)) {
        setErrorMessage(error.body.detail)
      } else {
        setErrorMessage(
          error instanceof Error ? error.message : 'Something went wrong. Try again.',
        )
      }
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      onClick={handleBackdropClick}
      className="w-full max-w-sm rounded-container border border-border bg-surface p-8"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-h2 text-text-primary">New event</h2>
        <button
          type="button"
          onClick={handleClose}
          aria-label="Close"
          className="text-text-secondary hover:text-text-primary"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-2">
          <label htmlFor="event-name" className="text-small font-medium text-text-primary">
            Name
          </label>
          <input
            id="event-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={createEvent.isPending}
            className="rounded-interactive border border-border bg-surface px-4 py-3 text-body text-text-primary disabled:text-text-disabled"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="event-date" className="text-small font-medium text-text-primary">
            Event date <span className="text-text-disabled">(optional)</span>
          </label>
          <input
            id="event-date"
            type="date"
            value={eventDate}
            onChange={(event) => setEventDate(event.target.value)}
            disabled={createEvent.isPending}
            className="rounded-interactive border border-border bg-surface px-4 py-3 text-body text-text-primary disabled:text-text-disabled"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="event-expires" className="text-small font-medium text-text-primary">
            Expires at
          </label>
          <input
            id="event-expires"
            type="datetime-local"
            required
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.target.value)}
            disabled={createEvent.isPending}
            className="rounded-interactive border border-border bg-surface px-4 py-3 text-body text-text-primary disabled:text-text-disabled"
          />
        </div>

        {errorMessage && (
          <div className="rounded-interactive bg-danger-bg px-4 py-3 text-small text-danger">
            {errorMessage}
          </div>
        )}

        <div className="mt-2 flex justify-end gap-4">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-interactive border border-border bg-surface px-6 py-3 text-body font-medium text-text-primary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createEvent.isPending}
            className="rounded-interactive bg-primary px-6 py-3 text-body font-medium text-on-primary hover:bg-primary-hover disabled:bg-surface-muted disabled:text-text-disabled"
          >
            {createEvent.isPending ? 'Creating...' : 'Create event'}
          </button>
        </div>
      </form>
    </dialog>
  )
}

function isDetailMessage(body: unknown): body is { detail: string } {
  return (
    typeof body === 'object' &&
    body !== null &&
    'detail' in body &&
    typeof (body as { detail: unknown }).detail === 'string'
  )
}
