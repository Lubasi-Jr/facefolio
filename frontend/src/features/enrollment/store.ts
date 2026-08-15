import { create } from 'zustand'

export type GuestFlowStep = 'consent' | 'capture' | 'enroll'

interface GuestFlowState {
  step: GuestFlowStep
  consent: boolean
  selfieBlob: Blob | null
  setStep: (step: GuestFlowStep) => void
  setConsent: (consent: boolean) => void
  setSelfieBlob: (blob: Blob) => void
  reset: () => void
}

const initialState = {
  step: 'consent' as GuestFlowStep,
  consent: false,
  selfieBlob: null,
}

// Holds guest-flow progress across the consent -> capture -> enroll steps.
// This is transient client state, not server state, so it lives outside
// TanStack Query — same pattern as the upload queue store. The consent flag
// and the captured selfie both have to survive here rather than in a single
// step's own state, since each step unmounts once the guest moves on, and
// the later enroll call needs both consent: true and the selfie together.
export const useGuestFlowStore = create<GuestFlowState>((set) => ({
  ...initialState,
  setStep: (step) => set({ step }),
  setConsent: (consent) => set({ consent }),
  setSelfieBlob: (blob) => set({ selfieBlob: blob }),
  reset: () => set(initialState),
}))
