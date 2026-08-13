export type UploadStatus = 'pending' | 'uploading' | 'confirming' | 'done' | 'failed'

export interface UploadItem {
  id: string
  file: File
  status: UploadStatus
  progress?: number
  error?: string
  photoId?: string
}

// Mirrors backend/app/schemas/photos.py

export interface PreparePhotoItem {
  filename: string
  size_bytes: number
}

export interface PreparedPhotoUpload {
  photo_id: string
  upload_url: string
}

export interface PreparePhotosResponse {
  photos: PreparedPhotoUpload[]
}

export interface PhotoConfirmResponse {
  photo_id: string
  status: 'queued'
}

export interface ProcessingStatus {
  awaiting_upload: number
  queued: number
  processing: number
  processed: number
  failed: number
}
