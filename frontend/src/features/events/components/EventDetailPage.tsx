import { useParams } from 'react-router-dom'

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="p-8">
      <h1 className="font-heading text-display text-primary">Event {id}</h1>
    </div>
  )
}
