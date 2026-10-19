"use client";

import * as React from "react";
import Link from "next/link";
import { OtpInput } from "@/components/auth/OtpInput";
import { resendVerification, verifyEmail } from "@/services/auth";

export function VerifyEmailForm({ initialEmail }: { initialEmail: string }) {
  const [email, setEmail] = React.useState(initialEmail);
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [seconds, setSeconds] = React.useState(60);

  React.useEffect(() => {
    if (seconds <= 0) return;
    const timer = window.setTimeout(() => setSeconds((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [seconds]);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try { await verifyEmail({ email, code }); setNotice("Your email is verified. You can sign in now."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to verify your email."); }
    finally { setBusy(false); }
  }

  async function resend() {
    setBusy(true); setError(""); setNotice("");
    try { const result = await resendVerification(email); setNotice(result.message); setSeconds(60); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to send a new code."); }
    finally { setBusy(false); }
  }

  return <form onSubmit={submit} className="space-y-5">
    <label className="grid gap-1.5 text-sm font-medium text-slate-700">Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="h-10 rounded-md border border-slate-300 px-3 text-slate-900 outline-none focus:ring-2 focus:ring-slate-200" /></label>
    <p className="text-sm text-slate-600">Enter the code sent to your email address.</p>
    <OtpInput value={code} onChange={setCode} disabled={busy || Boolean(notice)} />
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-700">{notice}</p>}
    {!notice && <button type="submit" disabled={busy || code.length !== 6} className="h-10 w-full rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">{busy ? "Checking…" : "Verify email"}</button>}
    <div className="flex items-center justify-between text-sm"><button type="button" onClick={() => void resend()} disabled={busy || seconds > 0 || Boolean(notice)} className="font-medium text-slate-700 underline underline-offset-4 disabled:cursor-not-allowed disabled:opacity-50">Resend code</button><span aria-live="polite" className="text-slate-500">{seconds > 0 ? `Available in ${seconds}s` : "You can request a new code"}</span></div>
    {notice && <Link href="/login" className="block text-center text-sm font-semibold text-slate-900 underline underline-offset-4">Go to sign in</Link>}
  </form>;
}
