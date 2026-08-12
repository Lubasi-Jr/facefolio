import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error = false, className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={clsx(
          "rounded-interactive border border-border bg-surface px-4 py-3 text-body text-text-primary w-full placeholder:text-text-disabled",
          "disabled:bg-background disabled:text-text-disabled disabled:cursor-not-allowed",
          error && "border-danger",
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";
