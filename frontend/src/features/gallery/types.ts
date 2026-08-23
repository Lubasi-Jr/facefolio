// Mirrors backend/app/schemas/photos.py — GalleryPhoto / GalleryResponse.
// The endpoint only ever returns processed photos, so every one of these
// is guaranteed to have a usable thumb_url.

export interface GalleryPhoto {
  photo_id: string
  web_url: string
  thumb_url: string
}

export interface GalleryResponse {
  photos: GalleryPhoto[]
}

// Mirrors backend/app/schemas/tags.py — PendingTag / PendingTagsResponse / TagReviewResponse
export interface PendingTag {
  photo_id: string
  similarity: number
  // Face crop if one was stored, otherwise the photo's thumbnail.
  crop_url: string
}

export interface PendingTagsResponse {
  tags: PendingTag[]
}

export type TagReviewDecision = 'confirm' | 'reject'
export type TagReviewStatus = 'confirmed' | 'rejected'

export interface TagReviewResponse {
  photo_id: string
  status: TagReviewStatus
  source: string
}
