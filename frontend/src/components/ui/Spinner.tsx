import { Loader2 } from "lucide-react";
import clsx from "clsx";

export type SpinnerSize = "sm" | "md" | "lg";

export interface SpinnerProps {
  size?: SpinnerSize;
  label?: string;
  center?: boolean;
  className?: string;
}

const sizePx: Record<SpinnerSize, number> = {
  sm: 16,
  md: 24,
  lg: 32,
};

export function Spinner({
  size = "md",
  label,
  center = false,
  className,
}: SpinnerProps) {
  const content = (
    <div className={clsx("flex items-center gap-2 text-body text-text-secondary", className)}>
      <Loader2 size={sizePx[size]} className="animate-spin text-text-secondary" />
      {label && <span>{label}</span>}
    </div>
  );

  if (center) {
    return (
      <div className="flex items-center justify-center py-12">{content}</div>
    );
  }

  return content;
}
