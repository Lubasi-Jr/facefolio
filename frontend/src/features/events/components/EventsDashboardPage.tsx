import { useState } from 'react'
import { Calendar, Plus } from 'lucide-react'
import { useEvents } from '../hooks/useEvents'
import { EventCard } from './EventCard'
import { CreateEventDialog } from './CreateEventDialog'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'

export function EventsDashboardPage() {
  const { data: events, isPending, isError } = useEvents()
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-display text-text-primary">Events</h1>
        <Button leftIcon={<Plus size={18} />} onClick={() => setDialogOpen(true)}>
          New event
        </Button>
      </div>

      <div className="mt-8">
        {isPending ? (
          <Spinner center label="Loading events" />
        ) : isError ? (
          <div className="rounded-interactive bg-danger-bg px-4 py-3 text-body text-danger">
            Couldn&apos;t load your events. Try refreshing.
          </div>
        ) : events.length === 0 ? (
          <EmptyState
            icon={<Calendar size={32} />}
            title="No events yet"
            description="Create your first event to start collecting photos."
            action={
              <Button leftIcon={<Plus size={18} />} onClick={() => setDialogOpen(true)}>
                New event
              </Button>
            }
          />
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
