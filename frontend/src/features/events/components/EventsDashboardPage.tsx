import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useEvents } from '../hooks/useEvents'
import { EventCard } from './EventCard'
import { CreateEventDialog } from './CreateEventDialog'

export function EventsDashboardPage() {
  const { data: events, isPending, isError } = useEvents()
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-display text-text-primary">Events</h1>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="flex items-center gap-2 rounded-interactive bg-primary px-6 py-3 text-body font-medium text-on-primary hover:bg-primary-hover"
        >
          <Plus className="h-4 w-4" />
          New event
        </button>
      </div>

      <div className="mt-8">
        {isPending ? (
          <p className="text-body text-text-secondary">Loading events...</p>
        ) : isError ? (
          <div className="rounded-interactive bg-danger-bg px-4 py-3 text-body text-danger">
            Couldn&apos;t load your events. Try refreshing.
          </div>
        ) : events.length === 0 ? (
          <p className="text-body text-text-secondary">
            No events yet. Create your first one to get started.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {events.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>

      <CreateEventDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  )
}
