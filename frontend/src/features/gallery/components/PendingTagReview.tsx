import { useState } from 'react'
import { Check, UserRoundSearch, X } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { usePendingTags } from '../hooks/usePendingTags'
import { useReviewTag } from '../hooks/useReviewTag'
import type { TagReviewDecision } from '../types'

interface PendingTagReviewProps {
  eventId: string
}

export function PendingTagReview({ eventId }: PendingTagReviewProps) {
  const { data, isPending, isError } = usePendingTags(eventId)
  const review = useReviewTag(eventId)
  // Tracked separately from review.isPending: that only reflects the most
  // recently started mutation, which would mark the wrong card "busy" if a
  // guest taps two cards before the first round trip finishes.
  const [busyPhotoIds, setBusyPhotoIds] = useState<Set<string>>(new Set())

  if (isPending || isError || data.tags.length === 0) return null

  function handleReview(photoId: string, decision: TagReviewDecision) {
    setBusyPhotoIds((prev) => new Set(prev).add(photoId))
    review.mutate(
      { photoId, decision },
      {
        onSettled: () => {
          setBusyPhotoIds((prev) => {
            const next = new Set(prev)
            next.delete(photoId)
            return next
          })
        },
      }
    )
  }

  return (
    <Card padding="sm" className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-text-primary">
        <UserRoundSearch size={18} />
        <h2 className="font-heading text-h3">Is this you?</h2>
      </div>
      <p className="text-small text-text-secondary">
        We&apos;re not fully sure about these — let us know so we get your gallery right.
      </p>
      <div className="flex gap-4 overflow-x-auto pb-1">
        {data.tags.map((tag) => {
          const isBusy = busyPhotoIds.has(tag.photo_id)
          return (
            <div key={tag.photo_id} className="flex w-24 flex-none flex-col items-center gap-2">
              <div className="aspect-square w-24 overflow-hidden rounded-container border border-border bg-surface-muted">
                <img src={tag.crop_url} alt="Possible match" className="h-full w-full object-cover" />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  aria-label="Yes, this is me"
                  disabled={isBusy}
                  onClick={() => handleReview(tag.photo_id, 'confirm')}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-success-bg text-success transition-colors duration-100 hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Check size={18} />
                </button>
                <button
                  type="button"
                  aria-label="No, that's not me"
                  disabled={isBusy}
                  onClick={() => handleReview(tag.photo_id, 'reject')}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-danger-bg text-danger transition-colors duration-100 hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <X size={18} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
