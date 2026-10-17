import Link from "next/link";
import { ArrowRight, CheckCircle2, Sparkles, Target } from "lucide-react";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200 bg-white p-7 shadow-sm sm:p-12">
        <Link href="/login" className="inline-flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
          <span className="flex size-11 items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white">A</span>
          <span className="text-lg font-bold tracking-tight text-slate-900">AURA</span>
        </Link>

        <div className="mt-14 max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
            <Sparkles aria-hidden="true" className="size-4" />
            Your personal routine workspace
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Make progress, one meaningful step at a time.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
            Keep your goals organized, follow deadlines, and see your progress in one clear workspace.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/register" className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
              Get started <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
            <Link href="/login" className="inline-flex items-center justify-center rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
              Sign in
            </Link>
          </div>
        </div>

        <div className="mt-14 grid gap-4 border-t border-slate-100 pt-7 sm:grid-cols-2">
          <div className="flex items-start gap-3 rounded-2xl bg-slate-50 p-4">
            <Target aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-blue-600" />
            <div><h2 className="text-sm font-semibold text-slate-900">Keep goals in view</h2><p className="mt-1 text-sm leading-5 text-slate-600">Create, update, and organize the goals that matter to you.</p></div>
          </div>
          <div className="flex items-start gap-3 rounded-2xl bg-slate-50 p-4">
            <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-blue-600" />
            <div><h2 className="text-sm font-semibold text-slate-900">See your progress</h2><p className="mt-1 text-sm leading-5 text-slate-600">Review goal status and upcoming deadlines at a glance.</p></div>
          </div>
        </div>
      </div>
    </main>
  );
}
