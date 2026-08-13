import { useCallback, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, KeyboardEvent } from 'react'
import { UploadCloud } from 'lucide-react'
import clsx from 'clsx'

interface DropzoneProps {
  onFilesSelected: (files: FileList) => void
}

function toImageFileList(files: FileList): FileList | null {
  const images = Array.from(files).filter((file) => file.type.startsWith('image/'))
  if (images.length === 0) return null

  const dataTransfer = new DataTransfer()
  images.forEach((file) => dataTransfer.items.add(file))
  return dataTransfer.files
}

export function Dropzone({ onFilesSelected }: DropzoneProps) {
  const [isDraggingOver, setIsDraggingOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return
      const imageFiles = toImageFileList(files)
      if (imageFiles) onFilesSelected(imageFiles)
    },
    [onFilesSelected]
  )

  const openPicker = () => inputRef.current?.click()

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openPicker()
    }
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDraggingOver(false)
    handleFiles(event.dataTransfer.files)
  }

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files)
    // reset so selecting the same file again still fires onChange
    event.target.value = ''
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Add photos"
      onClick={openPicker}
      onKeyDown={handleKeyDown}
      onDragOver={(event) => {
        event.preventDefault()
        setIsDraggingOver(true)
      }}
      onDragLeave={() => setIsDraggingOver(false)}
      onDrop={handleDrop}
      className={clsx(
        'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-container border-2 border-dashed px-8 py-16 text-center transition-colors duration-100',
        isDraggingOver
          ? 'border-primary bg-[color-mix(in_srgb,var(--color-primary)_8%,transparent)]'
          : 'border-border hover:border-primary hover:bg-[color-mix(in_srgb,var(--color-primary)_8%,transparent)]'
      )}
    >
      <UploadCloud className="h-8 w-8 text-text-secondary" />
      <div>
        <p className="text-body text-text-primary">
          Drag photos here, or <span className="font-medium text-primary">browse</span>
        </p>
        <p className="mt-1 text-small text-text-secondary">Images only</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleChange}
      />
    </div>
  )
}
