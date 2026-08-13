import { Image as ImageIcon } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useEventPhotos } from '../hooks/useEventPhotos'
import { PhotoGrid } from './PhotoGrid'

export function GalleryPanel({ eventId }: { eventId: string }) {
  const { data, isPending, isError } = useEventPhotos(eventId)

  return (
    <div>
      {isPending ? (
        <Spinner center label="Loading photos" />
      ) : isError ? (
        <div className="rounded-interactive bg-danger-bg px-4 py-3 text-body text-danger">
          Couldn&apos;t load photos. Try refreshing.
        </div>
      ) : data.photos.length === 0 ? (
        <EmptyState
          icon={<ImageIcon size={32} />}
          title="No photos yet"
          description="Processed photos will appear here as they finish."
        />
      ) : (
        <PhotoGrid photos={data.photos} />
      )}
    </div>
  )
}
