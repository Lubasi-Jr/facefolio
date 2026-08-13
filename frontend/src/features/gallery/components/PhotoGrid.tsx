import type { GalleryPhoto } from '../types'

export function PhotoGrid({ photos }: { photos: GalleryPhoto[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {photos.map((photo) => (
        <div
          key={photo.photo_id}
          className="aspect-square overflow-hidden rounded-container border border-border bg-surface"
        >
          <img
            src={photo.thumb_url}
            alt="Event photo"
            loading="lazy"
            className="h-full w-full object-cover"
          />
        </div>
      ))}
    </div>
  )
}
