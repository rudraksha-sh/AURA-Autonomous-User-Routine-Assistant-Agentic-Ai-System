"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, CalendarDays, Check, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { getGoals } from "@/services/goals";
import { generatePlan, PlannerApiError, savePlan } from "@/services/planner";
import type { Goal } from "@/types/goal";
import type { PlanPreview, ProposedPlanTask } from "@/types/planner";

function toLocalInput(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export default function PlannerPage() {
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [goalId, setGoalId] = React.useState("");
  const [plan, setPlan] = React.useState<PlanPreview | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [generating, setGenerating] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    getGoals().then((items) => {
      if (!active) return;
      setGoals(items);
      const firstGoal = items.find((goal) => goal.status === "active") ?? items[0];
      if (firstGoal) setGoalId(String(firstGoal.id));
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : "Unable to load your goals.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function onGenerate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!goalId) return;
    setGenerating(true); setError(null); setNotice(null); setPlan(null); setIdempotencyKey(null);
    try {
      setPlan(await generatePlan(Number(goalId)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate a plan.");
    } finally { setGenerating(false); }
  }

  function updateTask(index: number, change: Partial<ProposedPlanTask>) {
    setPlan((current) => current ? {
      ...current,
      tasks: current.tasks.map((task, taskIndex) => taskIndex === index ? { ...task, ...change } : task),
    } : current);
  }

  async function onSave() {
    if (!plan || !goalId || !plan.tasks.length) return;
    if (!window.confirm(`Save these ${plan.tasks.length} tasks to “${plan.goal_title}”?`)) return;
    const key = idempotencyKey ?? crypto.randomUUID();
    setIdempotencyKey(key); setSaving(true); setError(null); setNotice(null);
    try {
      await savePlan(Number(goalId), key, plan.tasks.map((task) => ({
        ...task,
        deadline: task.deadline ? new Date(task.deadline).toISOString() : null,
      })));
      setNotice("Your reviewed tasks are saved. They will appear in your task list and dashboard.");
      setPlan(null);
    } catch (err) {
      if (err instanceof PlannerApiError && err.status === 401) return;
      setError(err instanceof Error ? err.message : "Unable to save the plan. Retry to safely check the same submission.");
    } finally { setSaving(false); }
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Header userName="User" title="Plan with a goal" />
        <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900"><ArrowLeft aria-hidden="true" className="size-4" />Dashboard</Link>
          <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Build a practical plan</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">AURA uses a fixed set of planning rules and task templates. The suggestions are a starting point, not AI-generated advice. Review and edit every task before saving.</p>
            {error && <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
            {notice && <div role="status" className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><span className="flex items-center gap-2"><Check aria-hidden="true" className="size-4" />{notice}</span><Link href="/tasks" className="font-semibold underline">View tasks</Link></div>}
            {!loading && goals.length === 0 ? <div className="mt-6 rounded-xl bg-slate-50 p-5"><p className="text-sm text-slate-700">Create a goal before planning tasks.</p><Link href="/goals" className="mt-3 inline-flex font-semibold text-blue-600">Create a goal</Link></div> : (
              <form onSubmit={onGenerate} className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="min-w-0 flex-1"><label htmlFor="planner-goal" className="text-sm font-medium text-slate-700">Goal</label><select id="planner-goal" value={goalId} onChange={(event) => { setGoalId(event.target.value); setPlan(null); setIdempotencyKey(null); }} disabled={loading || generating || !goals.length} required className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm">{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select></div>
                <button type="submit" disabled={loading || generating || !goalId} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{generating ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <RefreshCw aria-hidden="true" className="size-4" />}{generating ? "Building plan…" : "Generate proposed tasks"}</button>
              </form>
            )}
            {loading && <p role="status" className="mt-6 text-sm text-slate-500">Loading your goals…</p>}
            {plan && <div className="mt-8 space-y-4">
              <div><h2 className="text-lg font-semibold text-slate-900">Review proposed tasks</h2><p className="mt-1 text-sm text-slate-500">Edit titles, descriptions, priorities, and dates. Dates are suggestions based on the goal deadline.</p></div>
              {plan.tasks.map((task, index) => <article key={`${task.position}-${index}`} className="rounded-xl border border-slate-200 p-4 sm:p-5">
                <div className="flex items-start justify-between gap-3"><h3 className="text-sm font-semibold text-slate-800">Task {index + 1}</h3><button type="button" aria-label={`Remove task ${index + 1}`} onClick={() => setPlan((current) => current ? { ...current, tasks: current.tasks.filter((_, taskIndex) => taskIndex !== index).map((item, position) => ({ ...item, position: position + 1 })) } : current)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700"><Trash2 aria-hidden="true" className="size-4" /></button></div>
                <label className="mt-3 block text-xs font-medium text-slate-600" htmlFor={`planner-title-${index}`}>Title</label><input id={`planner-title-${index}`} value={task.title} maxLength={255} onChange={(event) => updateTask(index, { title: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <label className="mt-3 block text-xs font-medium text-slate-600" htmlFor={`planner-description-${index}`}>Description</label><textarea id={`planner-description-${index}`} value={task.description ?? ""} maxLength={2000} rows={2} onChange={(event) => updateTask(index, { description: event.target.value || null })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <div className="mt-3 grid gap-3 sm:grid-cols-3"><div><label htmlFor={`planner-priority-${index}`} className="block text-xs font-medium text-slate-600">Priority</label><select id={`planner-priority-${index}`} value={task.priority} onChange={(event) => updateTask(index, { priority: event.target.value as ProposedPlanTask["priority"] })} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div><div><label htmlFor={`planner-estimate-${index}`} className="block text-xs font-medium text-slate-600">Minutes</label><input id={`planner-estimate-${index}`} type="number" min={5} max={480} value={task.estimated_minutes} onChange={(event) => updateTask(index, { estimated_minutes: Number(event.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div><div><label htmlFor={`planner-deadline-${index}`} className="block text-xs font-medium text-slate-600">Suggested deadline</label><div className="mt-1 flex items-center rounded-lg border border-slate-300 px-3"><CalendarDays aria-hidden="true" className="size-4 text-slate-400" /><input id={`planner-deadline-${index}`} type="datetime-local" value={toLocalInput(task.deadline)} onChange={(event) => updateTask(index, { deadline: event.target.value ? new Date(event.target.value).toISOString() : null })} className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none" /></div></div></div>
              </article>)}
              <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between"><button type="button" onClick={() => { setPlan(null); setIdempotencyKey(null); }} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel plan</button><button type="button" onClick={onSave} disabled={saving || !plan.tasks.length || plan.tasks.some((task) => !task.title.trim() || !Number.isInteger(task.estimated_minutes) || task.estimated_minutes < 5 || task.estimated_minutes > 480)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{saving && <Loader2 aria-hidden="true" className="size-4 animate-spin" />}{saving ? "Saving tasks…" : `Save ${plan.tasks.length} reviewed tasks`}</button></div>
            </div>}
          </section>
        </main>
      </div>
    </div>
  );
}
