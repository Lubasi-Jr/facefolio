import { useEffect } from 'react'
import { useUploadPhotos } from '../hooks/useUploadPhotos'
import { useProcessingStatus } from '../hooks/useProcessingStatus'
import { useUploadQueueStore } from '../store'
import { Dropzone } from './Dropzone'
import { UploadGrid } from './UploadGrid'
import { UploadProgressBar } from './UploadProgressBar'
import { ProcessingProgressBar } from './ProcessingProgressBar'

export function UploadPanel({ eventId }: { eventId: string }) {
  const items = useUploadQueueStore((state) => state.items)
  const resetQueue = useUploadQueueStore((state) => state.reset)
  const { uploadFiles, retryItem } = useUploadPhotos(eventId)
  const { data: processingStatus } = useProcessingStatus(eventId)

  // The upload queue is global Zustand state, but it should only ever show
  // the event currently being viewed. React Router reuses this component
  // instance across an eventId param change (it doesn't remount), so
  // without this the queue from whatever event was uploaded to last would
  // still be sitting here.
  useEffect(() => {
    resetQueue()
  }, [eventId, resetQueue])

  return (
    <div className="flex flex-col gap-8">
      <Dropzone onFilesSelected={uploadFiles} />

      {items.length > 0 && <UploadProgressBar items={items} />}

      {/* Reflects the event's whole processing pipeline, independent of
          this browser session's upload queue. */}
      {processingStatus && <ProcessingProgressBar status={processingStatus} />}

      {items.length > 0 && <UploadGrid items={items} onRetry={retryItem} />}
    </div>
  )
}
