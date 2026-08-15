// Direct-to-storage PUT, mirroring upload/api/storage.ts. Deliberately NOT
// routed through lib/api.ts: this goes to the Supabase Storage origin on a
// presigned URL, not our backend, so it must not carry an Authorization header.
export async function putBlobToStorage(uploadUrl: string, blob: Blob): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': blob.type || 'application/octet-stream' },
    body: blob,
  })

  if (!response.ok) {
    throw new Error(`Upload failed with status ${response.status}`)
  }
}
