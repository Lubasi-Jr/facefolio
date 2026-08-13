import { useEffect, useMemo } from 'react'
import { CheckCircle2, Loader2, RotateCcw, XCircle } from 'lucide-react'
import clsx from 'clsx'
import { Button } from '@/components/ui/Button'
import type { UploadItem, UploadStatus } from '../types'

const STATUS_LABEL: Record<UploadStatus, string> = {
  pending: 'Pending',
  uploading: 'Uploading',
  confirming: 'Confirming',
  done: 'Done',
  failed: 'Failed',
}

const STATUS_BADGE_BG: Partial<Record<UploadStatus, string>> = {
  uploading: 'bg-info',
  confirming: 'bg-info',
  done: 'bg-success',
  failed: 'bg-danger',
}

function StatusIcon({ status }: { status: UploadStatus }) {
  switch (status) {
    case 'uploading':
    case 'confirming':
      return <Loader2 className="h-3.5 w-3.5 animate-spin text-on-primary" />
    case 'done':
      return <CheckCircle2 className="h-3.5 w-3.5 text-on-primary" />
    case 'failed':
      return <XCircle className="h-3.5 w-3.5 text-on-primary" />
    default:
      return null
  }
}

interface UploadThumbnailProps {
  item: UploadItem
  onRetry: (id: string) => void
}

export function UploadThumbnail({ item, onRetry }: UploadThumbnailProps) {
  // One object URL per file, revoked on unmount/replacement so previews
  // don't leak memory as the queue grows.
  const previewUrl = useMemo(() => URL.createObjectURL(item.file), [item.file])
  useEffect(() => () => URL.revokeObjectURL(previewUrl), [previewUrl])

  const badgeBg = STATUS_BADGE_BG[item.status]

  return (
    <div className="flex flex-col gap-2">
      <div className="relative aspect-square overflow-hidden rounded-container border border-border bg-surface">
        <img src={previewUrl} alt={item.file.name} className="h-full w-full object-cover" />
        {badgeBg && (
          <span
            role="status"
            aria-label={STATUS_LABEL[item.status]}
            className={clsx(
              'absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full',
              badgeBg
            )}
          >
            <StatusIcon status={item.status} />
          </span>
        )}
      </div>

      <p className="truncate text-tiny text-text-secondary" title={item.file.name}>
        {item.file.name}
      </p>

      {item.status === 'failed' && (
        <div className="flex flex-col gap-1">
          {item.error && (
            <p className="truncate text-tiny text-danger" title={item.error}>
              {item.error}
            </p>
          )}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={() => onRetry(item.id)}
            aria-label={`Retry upload for ${item.file.name}`}
          >
            Retry
          </Button>
        </div>
      )}
    </div>
  )
}
