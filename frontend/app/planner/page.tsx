"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ListTodo, Plus } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { getGoals } from "@/services/goals";
import { ApiError } from "@/services/auth";
import { clearAccessToken } from "@/services/auth-storage";
import { createTask, TaskApiError } from "@/services/tasks";
import type { Goal } from "@/types/goal";

export default function PlannerPage() {
  const router = useRouter();
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [goalId, setGoalId] = React.useState("");
  const [title, setTitle] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    getGoals().then((items) => { setGoals(items); setGoalId(String(items.find((goal) => goal.status === "active")?.id ?? items[0]?.id ?? "")); })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) { clearAccessToken(); router.replace("/login"); return; }
        setError(err instanceof Error ? err.message : "Unable to load goals.");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function addNextStep(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!goalId || !title.trim()) return;
    setSaving(true); setError(null);
    try {
      await createTask(Number(goalId), { title: title.trim() });
      router.push("/tasks");
    } catch (err) {
      if (err instanceof TaskApiError && err.status === 401) { clearAccessToken(); router.replace("/login"); return; }
      setError(err instanceof Error ? err.message : "Unable to save your task.");
    }
    finally { setSaving(false); }
  }

  return <div className="min-h-screen bg-slate-50 md:flex"><Sidebar/><div className="min-w-0 flex-1"><Header userName="User" title="Plan with a goal"/><main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
    <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900"><ArrowLeft aria-hidden="true" className="size-4"/>Dashboard</Link>
    <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><span className="flex size-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600"><ListTodo aria-hidden="true" className="size-6"/></span><h2 className="mt-5 text-2xl font-bold tracking-tight text-slate-900">Choose one next step</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Connect a concrete task to one of your saved goals. AI planning is not configured yet, so this page saves only the step you enter.</p>
      {error && <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {!loading && goals.length === 0 ? <div className="mt-6 rounded-xl bg-slate-50 p-5"><p className="text-sm text-slate-700">Create a goal before adding a planned step.</p><Link href="/goals" className="mt-3 inline-flex items-center gap-2 font-semibold text-blue-600"><Plus aria-hidden="true" className="size-4"/>Create a goal</Link></div> : <form onSubmit={addNextStep} className="mt-6 space-y-4"><div><label htmlFor="planner-goal" className="text-sm font-medium text-slate-700">Goal</label><select id="planner-goal" value={goalId} onChange={(event) => setGoalId(event.target.value)} disabled={loading || !goals.length} required className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm">{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select></div><div><label htmlFor="planner-task" className="text-sm font-medium text-slate-700">Next step</label><input id="planner-task" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} required placeholder="e.g. Read chapter one" className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"/></div><button type="submit" disabled={saving || loading || !goals.length} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"><Plus aria-hidden="true" className="size-4"/>{saving ? "Saving..." : "Save next step"}</button></form>}
    </section>
  </main></div></div>;
}
