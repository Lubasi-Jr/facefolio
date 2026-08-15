import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Image as ImageIcon, SearchX } from 'lucide-react'
import clsx from 'clsx'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useEventPhotos } from '../hooks/useEventPhotos'
import { useMyPhotos } from '../hooks/useMyPhotos'
import { PhotoGrid } from './PhotoGrid'
import { Lightbox } from './Lightbox'
import type { GalleryPhoto } from '../types'

type Tab = 'mine' | 'all'

export function GuestGalleryPage() {
  const { id } = useParams<{ id: string }>()
  const eventId = id!
  const [tab, setTab] = useState<Tab>('mine')
  const [selectedPhoto, setSelectedPhoto] = useState<GalleryPhoto | null>(null)

  // Only the active tab's query is enabled — a guest who never switches off
  // "Photos of you" shouldn't also be polling the full-event feed.
  const mine = useMyPhotos(eventId, tab === 'mine')
  const all = useEventPhotos(eventId, tab === 'all')
  const active = tab === 'mine' ? mine : all

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 self-start px-4 py-8 sm:px-6">
      <div className="flex gap-1 rounded-interactive border border-border bg-surface p-1">
        <button
          type="button"
          onClick={() => setTab('mine')}
          className={clsx(
            'flex-1 rounded-interactive px-4 py-2 text-small font-medium transition-colors duration-100',
            tab === 'mine' ? 'bg-primary text-on-primary' : 'text-text-secondary hover:bg-background'
          )}
        >
          Photos of you
        </button>
        <button
          type="button"
          onClick={() => setTab('all')}
          className={clsx(
            'flex-1 rounded-interactive px-4 py-2 text-small font-medium transition-colors duration-100',
            tab === 'all' ? 'bg-primary text-on-primary' : 'text-text-secondary hover:bg-background'
          )}
        >
          All photos
        </button>
      </div>

      {active.isPending ? (
        <Spinner center label="Loading photos" />
      ) : active.isError ? (
        <div className="rounded-interactive bg-danger-bg px-4 py-3 text-body text-danger">
          Couldn&apos;t load photos. Try refreshing.
        </div>
      ) : active.data.photos.length === 0 ? (
        tab === 'mine' ? (
          <EmptyState
            icon={<SearchX size={32} />}
            title="We didn't find you yet"
            description="More photos may still be processing. Check back soon."
          />
        ) : (
          <EmptyState
            icon={<ImageIcon size={32} />}
            title="No photos yet"
            description="Processed photos will appear here as they finish."
          />
        )
      ) : (
        <PhotoGrid photos={active.data.photos} onPhotoClick={setSelectedPhoto} />
      )}

      <Lightbox photo={selectedPhoto} onClose={() => setSelectedPhoto(null)} />
    </div>
  )
}
