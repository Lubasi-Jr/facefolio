import type { ElementType, HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

export type CardPadding = "none" | "sm" | "md";

export interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  padding?: CardPadding;
  interactive?: boolean;
  children?: ReactNode;
}

const paddingClasses: Record<CardPadding, string> = {
  none: "p-0",
  sm: "p-4",
  md: "p-6",
};

export function Card({
  as: Component = "div",
  padding = "md",
  interactive = false,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <Component
      className={clsx(
        "bg-surface border border-border rounded-container",
        paddingClasses[padding],
        interactive &&
          "cursor-pointer hover:border-text-disabled transition-colors duration-100",
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
