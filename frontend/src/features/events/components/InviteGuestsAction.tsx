import { useState } from 'react'
import { Check, Copy, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useCreateInvitation } from '../hooks/useCreateInvitation'

export function InviteGuestsAction({ eventId }: { eventId: string }) {
  const { mutate, data, isPending, isError } = useCreateInvitation(eventId)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!data) return
    await navigator.clipboard.writeText(data.invite_link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        variant="secondary"
        leftIcon={<UserPlus size={18} />}
        isLoading={isPending}
        onClick={() => mutate()}
        className="self-start"
      >
        Invite guests
      </Button>

      {isError && (
        <p className="text-small text-danger">Couldn&apos;t create an invite link. Try again.</p>
      )}

      {data && (
        <div className="flex items-center gap-3 rounded-interactive border border-border bg-surface px-4 py-3">
          <span className="flex-1 truncate text-small text-text-secondary">
            {data.invite_link}
          </span>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={copied ? <Check size={16} /> : <Copy size={16} />}
            onClick={handleCopy}
            aria-label="Copy invite link"
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      )}
    </div>
  )
}
