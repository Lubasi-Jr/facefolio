import { useMutation } from '@tanstack/react-query'
import { enroll, prepareEnrollment } from '../api/enrollments'
import { putBlobToStorage } from '../api/storage'

interface EnrollInput {
  selfieBlob: Blob
  consent: boolean
}

export function useEnroll(eventId: string) {
  return useMutation({
    mutationFn: async ({ selfieBlob, consent }: EnrollInput) => {
      const prepared = await prepareEnrollment(eventId)
      await putBlobToStorage(prepared.upload_url, selfieBlob)

      // Send back prepared.selfie_key exactly as the backend handed it out —
      // never a key read from the storage PUT response. Supabase's upload
      // response prepends the bucket name (e.g. "event-media/events/...")
      // and the backend's /enroll expects the bare key
      // ("events/{event_id}/enrollments/{user_id}.webp").
      return enroll(eventId, { selfie_key: prepared.selfie_key, consent })
    },
  })
}
