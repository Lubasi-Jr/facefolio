// Mirrors backend/app/schemas/invitations.py — InvitationPublicRead
export type JoinStatus = 'joinable' | 'revoked' | 'expired'

export interface InvitationPublic {
  event_id: string
  event_name: string
  join_status: JoinStatus
}

// Mirrors backend/app/schemas/enrollments.py
export interface PrepareEnrollmentResponse {
  selfie_key: string
  upload_url: string
}

export interface EnrollRequest {
  selfie_key: string
  consent: boolean
}

export interface EnrollResponse {
  // Confirmed matches only — the immediate "Photos of you" result.
  matched_count: number
  matched_photo_ids: string[]
  // Matches banded 'pending_guest': already stored as tags, but need guest
  // confirmation before they count as "yours" (see PendingTagReview).
  pending_review_count: number
}
