import type { LabelHTMLAttributes } from "react";
import clsx from "clsx";

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  htmlFor: string;
}

export function Label({ htmlFor, className, children, ...props }: LabelProps) {
  return (
    <label
      htmlFor={htmlFor}
      className={clsx("text-small font-medium text-text-primary", className)}
      {...props}
    >
      {children}
    </label>
  );
}
