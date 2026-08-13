interface ProgressBarProps {
  label: string
  current: number
  total: number
}

export function ProgressBar({ label, current, total }: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between text-small">
        <span className="font-medium text-text-primary">{label}</span>
        <span className="text-text-secondary">
          {current} / {total}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-150"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
