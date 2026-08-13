import { useParams } from 'react-router-dom'
import { CalendarDays, Clock } from 'lucide-react'
import { formatDate } from '@/utils/formatDate'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { UploadPanel } from '@/features/upload'
import { GalleryPanel } from '@/features/gallery'
import { useEvent } from '../hooks/useEvent'
import { InviteGuestsAction } from './InviteGuestsAction'
import { DeleteEventAction } from './DeleteEventAction'
import type { EventStatus } from '../types'

const STATUS_STYLES: Record<EventStatus, string> = {
  active: 'bg-success-bg text-success',
  expired: 'bg-warning-bg text-warning',
  purged: 'bg-danger-bg text-danger',
}

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: event, isPending, isError } = useEvent(id!)

  if (isPending) {
    return <Spinner center label="Loading event" />
  }

  if (isError) {
    return (
      <EmptyState
        icon={<CalendarDays size={32} />}
        title="Couldn't load this event"
        description="It may not exist, or you may not have access to it."
      />
    )
  }

  return (
    <div className="flex flex-col gap-8 p-8">
      <div className="flex flex-col gap-6 border-b border-border pb-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h1 className="font-heading text-display text-text-primary">{event.name}</h1>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-small text-text-secondary">
              {event.event_date && (
                <span className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4" />
                  {formatDate(event.event_date)}
                </span>
              )}
              <span className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Expires {formatDate(event.expires_at)}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-3">
            <span
              className={`rounded-full px-3 py-1 text-tiny font-medium ${STATUS_STYLES[event.status]}`}
            >
              {event.status}
            </span>
            <DeleteEventAction eventId={event.id} eventName={event.name} />
          </div>
        </div>

        <InviteGuestsAction eventId={event.id} />
      </div>

      <UploadPanel eventId={event.id} />
      <GalleryPanel eventId={event.id} />
    </div>
  )
}
