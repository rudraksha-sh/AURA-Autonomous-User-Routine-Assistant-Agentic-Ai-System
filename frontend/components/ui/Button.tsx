import * as React from "react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "default" | "sm" | "lg";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "default",
      size = "default",
      ...props
    },
    ref
  ) => {
    const variants = {
      default:
        "bg-slate-900 text-white hover:bg-slate-700",
      outline:
        "border border-slate-300 bg-white text-slate-900 hover:bg-slate-50",
      ghost:
        "text-slate-700 hover:bg-slate-100",
      destructive:
        "bg-red-600 text-white hover:bg-red-700",
    };

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-9 rounded-md px-3",
      lg: "h-11 rounded-md px-8",
    };

    return (
      <button
        ref={ref}
        className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors outline-none focus:ring-2 focus:ring-slate-300 disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";