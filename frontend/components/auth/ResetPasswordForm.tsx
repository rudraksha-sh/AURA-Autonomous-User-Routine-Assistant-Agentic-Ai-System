"use client";

import * as React from "react";
import Link from "next/link";
import { OtpInput } from "@/components/auth/OtpInput";
import { resetPassword } from "@/services/auth";

export function ResetPasswordForm({ initialEmail }: { initialEmail: string }) {
  const [email, setEmail] = React.useState(initialEmail);
  const [code, setCode] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [done, setDone] = React.useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 8 || password.length > 100) { setError("Password must be 8 to 100 characters."); return; }
    setBusy(true);
    try { await resetPassword({ email, code, new_password: password }); setDone(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to reset your password."); }
    finally { setBusy(false); }
  }
  if (done) return <div className="space-y-4"><p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">Your password was reset. You can sign in with your new password.</p><Link href="/login" className="block text-center text-sm font-semibold text-slate-900 underline underline-offset-4">Go to sign in</Link></div>;
  return <form onSubmit={submit} className="space-y-5">
    <label className="grid gap-1.5 text-sm font-medium text-slate-700">Email<input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="h-10 rounded-md border border-slate-300 px-3 outline-none focus:ring-2 focus:ring-slate-200" /></label>
    <OtpInput value={code} onChange={setCode} disabled={busy} />
    <p className="text-xs text-slate-500">Password must be 8–100 characters.</p>
    <label className="grid gap-1.5 text-sm font-medium text-slate-700">New password<input type="password" required minLength={8} maxLength={100} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="h-10 rounded-md border border-slate-300 px-3 outline-none focus:ring-2 focus:ring-slate-200" /></label>
    <label className="grid gap-1.5 text-sm font-medium text-slate-700">Confirm new password<input type="password" required minLength={8} maxLength={100} autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} className="h-10 rounded-md border border-slate-300 px-3 outline-none focus:ring-2 focus:ring-slate-200" /></label>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    <button type="submit" disabled={busy || code.length !== 6} className="h-10 w-full rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">{busy ? "Saving…" : "Reset password"}</button>
    <p className="text-center text-sm text-slate-500"><Link href="/login" className="font-medium text-slate-900 underline underline-offset-4">Back to sign in</Link></p>
  </form>;
}
