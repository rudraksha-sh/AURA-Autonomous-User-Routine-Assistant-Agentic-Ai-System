"use client";

import * as React from "react";

export function OtpInput({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const refs = React.useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length: 6 }, (_, index) => value[index] ?? "");

  function applyInput(index: number, raw: string) {
    const pasted = raw.replace(/\D/g, "").slice(0, 6);
    const next = [...digits];
    if (pasted.length > 1) {
      const start = pasted.length === 6 ? 0 : index;
      for (let offset = 0; offset < pasted.length && start + offset < 6; offset += 1) {
        next[start + offset] = pasted[offset];
      }
      onChange(next.join("").slice(0, 6));
      refs.current[Math.min(start + pasted.length, 5)]?.focus();
      return;
    }
    next[index] = pasted;
    onChange(next.join(""));
    if (pasted && index < 5) refs.current[index + 1]?.focus();
  }

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-slate-700">6-digit code</legend>
      <div className="flex justify-between gap-2" role="group" aria-label="6-digit verification code">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(node) => { refs.current[index] = node; }}
            aria-label={`Code digit ${index + 1}`}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete={index === 0 ? "one-time-code" : "off"}
            maxLength={6}
            value={digit}
            disabled={disabled}
            onChange={(event) => applyInput(index, event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Backspace" && !digit && index > 0) refs.current[index - 1]?.focus();
              if (event.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
              if (event.key === "ArrowRight" && index < 5) refs.current[index + 1]?.focus();
            }}
            onPaste={(event) => {
              const pasted = event.clipboardData.getData("text");
              if (pasted.replace(/\D/g, "").length > 1) {
                event.preventDefault();
                applyInput(index, pasted);
              }
            }}
            className="h-12 min-w-0 w-12 rounded-lg border border-slate-300 text-center text-lg font-semibold text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          />
        ))}
      </div>
    </fieldset>
  );
}
