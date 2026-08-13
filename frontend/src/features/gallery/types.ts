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
