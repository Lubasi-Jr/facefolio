import { useParams } from 'react-router-dom'

export function JoinPage() {
  const { token } = useParams<{ token: string }>()

  return (
    <div className="p-8">
      <h1 className="font-heading text-display text-primary">Join {token}</h1>
    </div>
  )
}
