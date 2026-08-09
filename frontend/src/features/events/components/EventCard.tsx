import { Link } from 'react-router-dom'
import { CalendarDays } from 'lucide-react'
import { formatDate } from '@/utils/formatDate'
import type { Event, EventStatus } from '../types'

const STATUS_STYLES: Record<EventStatus, string> = {
  active: 'bg-success-bg text-success',
  expired: 'bg-warning-bg text-warning',
  purged: 'bg-danger-bg text-danger',
}

export function EventCard({ event }: { event: Event }) {
  return (
    <Link
      to={`/events/${event.id}`}
      className="flex flex-col gap-4 rounded-container border border-border bg-surface p-6 hover:border-primary"
    >
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-h3 font-semibold text-text-primary">{event.name}</h3>
        <span
          className={`shrink-0 rounded-full px-3 py-1 text-tiny font-medium ${STATUS_STYLES[event.status]}`}
        >
          {event.status}
        </span>
      </div>

      {event.event_date && (
        <div className="flex items-center gap-2 text-small text-text-secondary">
          <CalendarDays className="h-4 w-4" />
          <span>{formatDate(event.event_date)}</span>
        </div>
      )}
    </Link>
  )
}
