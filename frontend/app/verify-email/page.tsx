import type { Metadata } from "next";
import { VerifyEmailForm } from "@/components/auth/VerifyEmailForm";

export const metadata: Metadata = { title: "Verify email — AURA" };

export default async function VerifyEmailPage({ searchParams }: { searchParams: Promise<{ email?: string | string[] }> }) {
  const params = await searchParams;
  const email = Array.isArray(params.email) ? params.email[0] : params.email;
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12"><div className="w-full max-w-sm"><header className="mb-6 text-center"><div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-xl font-bold text-white">A</div><h1 className="text-3xl font-bold tracking-tight text-slate-900">Verify your email</h1><p className="mt-2 text-sm text-slate-500">Enter the one-time code sent by AURA.</p></header><div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><VerifyEmailForm initialEmail={email ?? ""} /></div></div></main>;
}
