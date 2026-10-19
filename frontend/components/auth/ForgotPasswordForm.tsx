"use client";

import * as React from "react";
import Link from "next/link";
import { forgotPassword } from "@/services/auth";

export function ForgotPasswordForm() {
  const [email, setEmail] = React.useState("");
  const [error, setError] = React.useState("");
  const [sent, setSent] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await forgotPassword(email); setSent(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to request a reset code."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="space-y-5">
    <label className="grid gap-1.5 text-sm font-medium text-slate-700">Email<input type="email" autoComplete="email" required maxLength={255} value={email} onChange={(event) => setEmail(event.target.value)} className="h-10 rounded-md border border-slate-300 px-3 text-slate-900 outline-none focus:ring-2 focus:ring-slate-200" /></label>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    {sent ? <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">If an account exists for that email, we sent a code.</p> : <button type="submit" disabled={busy} className="h-10 w-full rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">{busy ? "Sending…" : "Send reset code"}</button>}
    {sent && <Link href={`/reset-password?email=${encodeURIComponent(email)}`} className="block text-center text-sm font-semibold text-slate-900 underline underline-offset-4">Enter reset code</Link>}
    <p className="text-center text-sm text-slate-500"><Link href="/login" className="font-medium text-slate-900 underline underline-offset-4">Back to sign in</Link></p>
  </form>;
}
