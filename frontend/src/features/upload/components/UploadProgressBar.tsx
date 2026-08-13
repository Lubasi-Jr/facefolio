import { ProgressBar } from './ProgressBar'
import type { UploadItem } from '../types'

export function UploadProgressBar({ items }: { items: UploadItem[] }) {
  const done = items.filter((item) => item.status === 'done').length
  const failed = items.filter((item) => item.status === 'failed').length

  return (
    <div className="flex flex-col gap-1">
      <ProgressBar label="Uploading" current={done} total={items.length} />
      {failed > 0 && <p className="text-tiny text-danger">{failed} failed</p>}
    </div>
  )
}
