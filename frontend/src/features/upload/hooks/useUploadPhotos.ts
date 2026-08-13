import { useCallback, useRef } from 'react'
import { runPool } from '@/utils/runPool'
import { confirmPhoto, preparePhotos } from '../api/upload'
import { putFileToStorage } from '../api/storage'
import { useUploadQueueStore } from '../store'

const PREPARE_BATCH_SIZE = 25
const UPLOAD_CONCURRENCY = 5
const MAX_PUT_RETRIES = 2
const RETRY_BACKOFF_MS = 500

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let i = 0; i < items.length; i += size) {
    chunks.push(items.slice(i, i + size))
  }
  return chunks
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

interface PreparedUpload {
  id: string
  file: File
  photoId: string
  uploadUrl: string
}

// Orchestrates a batch of files from file-select through to confirmed
// upload. Two distinct concurrency schemes are at play: prepare requests go
// out sequentially in batches of 25 (each batch creates 25 DB rows on the
// backend), while the PUT+confirm step for individual files runs through a
// sliding-window pool of 5 so one slow or failing file never blocks the rest.
export function useUploadPhotos(eventId: string) {
  const addFiles = useUploadQueueStore((state) => state.addFiles)
  const updateItem = useUploadQueueStore((state) => state.updateItem)

  // Prepared uploads are cached by item id (not in the Zustand queue —
  // nothing in the UI needs a raw upload_url). A manual retry reuses this
  // instead of calling prepare again, since the backend hands out one-time
  // signed upload URLs (see storage_client.create_signed_upload_url).
  const preparedUploadsRef = useRef(new Map<string, PreparedUpload>())
  // Tracks items whose PUT already succeeded, so retrying a confirm-only
  // failure doesn't re-PUT to an upload URL that's already been consumed.
  const putDoneRef = useRef(new Set<string>())

  const runUpload = useCallback(
    async (upload: PreparedUpload) => {
      if (!putDoneRef.current.has(upload.id)) {
        updateItem(upload.id, { status: 'uploading', error: undefined })

        let putSucceeded = false
        for (let attempt = 0; attempt <= MAX_PUT_RETRIES; attempt++) {
          try {
            await putFileToStorage(upload.uploadUrl, upload.file)
            putSucceeded = true
            break
          } catch (error) {
            if (attempt === MAX_PUT_RETRIES) {
              updateItem(upload.id, {
                status: 'failed',
                error: error instanceof Error ? error.message : 'Upload failed',
              })
              return
            }
            await wait(RETRY_BACKOFF_MS * (attempt + 1))
          }
        }
        if (putSucceeded) putDoneRef.current.add(upload.id)
      }

      updateItem(upload.id, { status: 'confirming' })

      try {
        await confirmPhoto(eventId, upload.photoId)
        updateItem(upload.id, { status: 'done' })
      } catch (error) {
        updateItem(upload.id, {
          status: 'failed',
          error: error instanceof Error ? error.message : 'Could not confirm upload',
        })
      }
    },
    [eventId, updateItem]
  )

  const uploadFiles = useCallback(
    async (fileList: FileList) => {
      const newItems = addFiles(fileList)
      if (newItems.length === 0) return

      const preparedUploads: PreparedUpload[] = []

      for (const batch of chunk(newItems, PREPARE_BATCH_SIZE)) {
        try {
          const response = await preparePhotos(
            eventId,
            batch.map((item) => ({ filename: item.file.name, size_bytes: item.file.size }))
          )
          response.photos.forEach((prepared, index) => {
            const item = batch[index]
            const upload: PreparedUpload = {
              id: item.id,
              file: item.file,
              photoId: prepared.photo_id,
              uploadUrl: prepared.upload_url,
            }
            updateItem(item.id, { photoId: prepared.photo_id })
            preparedUploadsRef.current.set(item.id, upload)
            preparedUploads.push(upload)
          })
        } catch (error) {
          // The whole batch failed to prepare (e.g. quota exceeded) — none of
          // these items got a photoId, so none of them can be uploaded.
          batch.forEach((item) => {
            updateItem(item.id, {
              status: 'failed',
              error: error instanceof Error ? error.message : 'Could not prepare upload',
            })
          })
        }
      }

      await runPool(preparedUploads, runUpload, UPLOAD_CONCURRENCY)
    },
    [eventId, addFiles, updateItem, runUpload]
  )

  const retryItem = useCallback(
    async (id: string) => {
      let upload = preparedUploadsRef.current.get(id)

      if (!upload) {
        // Never got a photoId — its original prepare batch failed outright.
        // Prepare it fresh, as a batch of one.
        const item = useUploadQueueStore.getState().items.find((i) => i.id === id)
        if (!item) return

        updateItem(id, { status: 'pending', error: undefined })

        try {
          const response = await preparePhotos(eventId, [
            { filename: item.file.name, size_bytes: item.file.size },
          ])
          const prepared = response.photos[0]
          upload = {
            id,
            file: item.file,
            photoId: prepared.photo_id,
            uploadUrl: prepared.upload_url,
          }
          updateItem(id, { photoId: prepared.photo_id })
          preparedUploadsRef.current.set(id, upload)
        } catch (error) {
          updateItem(id, {
            status: 'failed',
            error: error instanceof Error ? error.message : 'Could not prepare upload',
          })
          return
        }
      } else {
        updateItem(id, { error: undefined })
      }

      await runUpload(upload)
    },
    [eventId, updateItem, runUpload]
  )

  return { uploadFiles, retryItem }
}
