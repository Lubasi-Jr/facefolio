// Direct-to-storage PUT. Deliberately NOT routed through lib/api.ts: this
// goes to the Supabase Storage origin on a presigned URL, not our backend,
// so it must not carry an Authorization header.
export async function putFileToStorage(uploadUrl: string, file: File): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  })

  if (!response.ok) {
    throw new Error(`Upload failed with status ${response.status}`)
  }
}
