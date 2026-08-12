import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-3 py-16">
      <div className="rounded-full bg-background p-4 text-text-disabled">
        {icon}
      </div>
      <h3 className="font-heading text-h3 text-text-primary">{title}</h3>
      {description && (
        <p className="text-body text-text-secondary max-w-sm">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
