import { ProgressBar } from './ProgressBar'
import type { ProcessingStatus } from '../types'

export function ProcessingProgressBar({ status }: { status: ProcessingStatus }) {
  const total =
    status.awaiting_upload + status.queued + status.processing + status.processed + status.failed

  return (
    <div className="flex flex-col gap-1">
      <ProgressBar label="Processing" current={status.processed} total={total} />
      {status.failed > 0 && <p className="text-tiny text-danger">{status.failed} failed</p>}
    </div>
  )
}
