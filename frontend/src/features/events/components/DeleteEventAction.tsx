import { useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useDeleteEvent } from '../hooks/useDeleteEvent'

export function DeleteEventAction({ eventId, eventName }: { eventId: string; eventName: string }) {
  const navigate = useNavigate()
  const { mutate, isPending, isError } = useDeleteEvent()

  const handleDelete = () => {
    const confirmed = window.confirm(
      `Delete "${eventName}"? This permanently removes its photos and guest data and can't be undone.`,
    )
    if (!confirmed) return

    mutate(eventId, {
      onSuccess: () => navigate('/events'),
    })
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button
        variant="danger"
        size="sm"
        leftIcon={<Trash2 size={16} />}
        isLoading={isPending}
        onClick={handleDelete}
      >
        Delete event
      </Button>
      {isError && (
        <p className="text-small text-danger">Couldn&apos;t delete this event. Try again.</p>
      )}
    </div>
  )
}
