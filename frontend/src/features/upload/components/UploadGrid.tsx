import type { UploadItem } from '../types'
import { UploadThumbnail } from './UploadThumbnail'

interface UploadGridProps {
  items: UploadItem[]
  onRetry: (id: string) => void
}

export function UploadGrid({ items, onRetry }: UploadGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {items.map((item) => (
        <UploadThumbnail key={item.id} item={item} onRetry={onRetry} />
      ))}
    </div>
  )
}
