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
  matched_count: number
  matched_photo_ids: string[]
}
