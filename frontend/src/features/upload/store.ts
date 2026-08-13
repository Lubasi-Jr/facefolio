import { create } from 'zustand'
import type { UploadItem } from './types'

interface UploadQueueState {
  items: UploadItem[]
  addFiles: (files: FileList) => UploadItem[]
  updateItem: (id: string, updates: Partial<UploadItem>) => void
  removeItem: (id: string) => void
  clearCompleted: () => void
  reset: () => void
}

export const useUploadQueueStore = create<UploadQueueState>((set) => ({
  items: [],

  addFiles: (files) => {
    const newItems: UploadItem[] = Array.from(files).map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
    }))
    set((state) => ({ items: [...state.items, ...newItems] }))
    // Returned so the upload orchestration can correlate these items with
    // the prepare-batch response without re-deriving them from state.
    return newItems
  },

  updateItem: (id, updates) =>
    set((state) => ({
      items: state.items.map((item) => (item.id === id ? { ...item, ...updates } : item)),
    })),

  removeItem: (id) =>
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
    })),

  clearCompleted: () =>
    set((state) => ({
      items: state.items.filter((item) => item.status !== 'done'),
    })),

  reset: () => set({ items: [] }),
}))
