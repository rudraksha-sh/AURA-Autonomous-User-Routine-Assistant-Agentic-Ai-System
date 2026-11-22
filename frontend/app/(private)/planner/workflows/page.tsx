"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";

import { AutonomyControls } from "@/components/workflows/AutonomyControls";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { getGoals } from "@/services/goals";
import { listAutonomyGrants, listWorkflows, startReplan, startSimulationWorkflow, startWorkflow, transitionWorkflow, undoWorkflow } from "@/services/planner";
import type { Goal } from "@/types/goal";
import type { AutonomyGrant, Workflow, WorkflowOperation } from "@/types/workflow";

const statuses: Record<Workflow["status"], string> = {
  awaiting_approval: "Awaiting approval",
  paused: "Paused",
  cancelled: "Cancelled",
  rejected: "Rejected",
  completed: "Completed",
  undone: "Tasks removed",
};

const card = "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-6";
const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-600";
const primary = "bg-blue-600! text-white! hover:bg-blue-700!";
const quiet = "text-sm text-slate-600 dark:text-slate-300";

export default function WorkflowsPage() {
  const [grants, setGrants] = useState<AutonomyGrant[]>([]);
  const [grantId, setGrantId] = useState("");
  const [goals, setGoals] = useState<Goal[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<string>();
  const [goalId, setGoalId] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pendingStart, setPendingStart] = useState<{ key: string; input: string }>();

  useEffect(() => {
    let active = true;
    Promise.all([getGoals(), listWorkflows(), listAutonomyGrants()]).then(([goalList, runList, grantList]) => {
      if (!active) return;
      setGoals(goalList);
      setGrants(grantList);
      setGoalId(goalList.length ? String(goalList[0].id) : "");
      setWorkflows(runList);
      setSelected(runList[0]?.id);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Unable to load workflows.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const grant = grants.find((item) => item.id === grantId && item.status === "active" && item.goal_id === Number(goalId));
  const run = workflows.find((item) => item.id === selected);

  function show(item: Workflow) {
    setWorkflows((current) => current.some(({ id }) => id === item.id)
      ? current.map((existing) => existing.id === item.id ? item : existing)
      : [item, ...current]);
    setSelected(item.id);
  }

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = JSON.stringify([goalId, targetDate, grant?.id]);
    const key = pendingStart?.input === input ? pendingStart.key : crypto.randomUUID();
    setPendingStart({ input, key });
    setBusy(true);
    setError("");
    try {
      show(await startWorkflow(key, Number(goalId), targetDate, grant));
      setGrantId("");
      if (grant) setGrants(await listAutonomyGrants());
      setPendingStart(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to start workflow.");
    } finally {
      setBusy(false);
    }
  }

  async function previewAlternative(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (event) {
        const values = new FormData(event.currentTarget);
        show(await startSimulationWorkflow(crypto.randomUUID(), {
          target_date: String(values.get("day")), capacity_minutes: Number(values.get("capacity")),
        }));
      } else if (run?.goal_id && run.result.schedule) {
        show(await startReplan(crypto.randomUUID(), run.goal_id, run.id, run.result.schedule.target_date));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to run the preview.");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const [runs, currentGrants] = await Promise.all([listWorkflows(), listAutonomyGrants()]);
      setWorkflows(runs);
      setGrants(currentGrants);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to refresh workflows.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(operation: WorkflowOperation | "undo") {
    if (!run || (operation === "undo" && !window.confirm("Remove the unchanged tasks created by this run?"))) return;
    setBusy(true);
    setError("");
    try {
      show(await (operation === "undo" ? undoWorkflow(run) : transitionWorkflow(run, operation)));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update workflow.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 md:flex">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Header userName="User" title="Agent workflows" />
        <main className="mx-auto grid w-full max-w-6xl gap-5 px-4 py-8 sm:px-6">
          <div>
            <Link href="/planner" className="text-sm font-medium underline">Back to planner</Link>
            <h1 className="mt-3 text-3xl font-bold tracking-tight">Agent workflows</h1>
            <p className={quiet}>Preview proposed tasks and estimate how they fit into a workday. Approve the plan to create tasks for your goal.</p>
          </div>
          {error && <p role="alert" className="rounded-lg border border-rose-300 p-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
          {loading && <p role="status" className={quiet}>Loading goals and workflowsâ€¦</p>}
          <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(15rem,1fr)_minmax(0,2fr)]">
            <div className="contents lg:grid lg:content-start lg:gap-5">
              <section className={`order-1 ${card}`}>
                <h2 className="text-lg font-semibold">New plan</h2>
                {!loading && goals.length === 0 ? (
                  <Link href="/goals" className="mt-3 inline-block text-sm underline">Create a goal to start</Link>
                ) : (
                  <form onSubmit={start} className="mt-4 grid gap-4">
                    <label className="text-sm font-medium">
                      Goal
                      <select className={field} value={goalId} onChange={(event) => { setGoalId(event.target.value); setGrantId(""); }} required>
                        {goals.map((goal) => <option key={goal.id} value={goal.id} className="dark:bg-slate-900">{goal.title}</option>)}
                      </select>
                    </label>
                    <label className="text-sm font-medium">
                      Schedule preview date
                      <input className={field} type="date" required value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
                    </label>
                    <Button disabled={loading || busy || !goalId} type="submit" className={primary}>{grant ? "Create tasks with selected grant" : "Preview plan"}</Button>
                  </form>
                )}
              </section>
              <section className={`order-3 ${card}`}>
                <h2 className="text-lg font-semibold">Simulate a shorter workday</h2>
                <form onSubmit={previewAlternative} className="mt-3 grid gap-3 text-sm">
                  <label>Scenario date<input name="day" type="date" className={field} required /></label>
                  <label>Available minutes<input name="capacity" type="number" min={30} max={720} className={field} required /></label>
                  <Button type="submit" variant="outline" disabled={loading || busy}>Run simulation</Button>
                </form>
              </section>
              <AutonomyControls goals={goals} grants={grants} selectedGrant={grantId} disabled={loading || busy}
                onSelect={(value) => {
                  setGrantId(value);
                  const selectedGrant = grants.find((item) => item.id === value);
                  if (selectedGrant?.goal_id) setGoalId(String(selectedGrant.goal_id));
                }}
                onChange={(changed) => {
                  setGrantId("");
                  if (changed) setGrants((items) => [changed, ...items.filter((item) => item.id !== changed.id)]);
                  else setGrants((items) => items.map((item) => ({ ...item, status: "revoked" })));
                }} />
              <section className={`order-5 ${card}`}>
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold">Recent workflows</h2>
                  <Button variant="outline" size="sm" disabled={loading || busy} onClick={refresh}>Refresh</Button>
                </div>
                {!loading && workflows.length === 0 && <p className={quiet}>Your workflow history will appear here.</p>}
                <ul className="mt-3 grid gap-2">
                  {workflows.map((item) => (
                    <li key={item.id}>
                      <button type="button" disabled={busy} aria-pressed={selected === item.id}
                        onClick={() => setSelected(item.id)}
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-start text-sm aria-pressed:border-blue-500 focus-visible:outline-2 focus-visible:outline-blue-500 dark:border-slate-700 dark:aria-pressed:border-blue-400">
                        <span className="block break-words font-medium">{item.result.plan?.goal_title ?? "Schedule simulation"}</span>
                        <span className={quiet}>{statuses[item.status]} Â· {new Date(item.created_at).toLocaleDateString()}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
            {run && (
              <section className={`order-2 ${card} lg:order-none`} aria-busy={busy}>
                <h2 className="break-words text-xl font-semibold">{run.result.plan?.goal_title ?? "Schedule simulation"}</h2>
                <p className={quiet} role="status">{statuses[run.status]}</p>
                {run.result.plan && (
                  <ol className="my-5 grid gap-3">
                    {run.result.plan.tasks.map((task) => (
                      <li key={task.position} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                        <p className="break-words font-medium">{task.title}</p>
                        <p className={quiet}>{task.estimated_minutes} min Â· {task.priority} priority{task.deadline && ` Â· Due ${new Date(task.deadline).toLocaleString()}`}</p>
                        {task.description && <p className={`mt-1 break-words ${quiet}`}>{task.description}</p>}
                      </li>
                    ))}
                  </ol>
                )}
                {run.result.schedule && (
                  <div className="my-5">
                    <h3 className="font-semibold">Schedule estimate</h3>
                    <p className={quiet}>{run.result.schedule.target_date} Â· {run.result.schedule.scheduled_minutes} of {run.result.schedule.capacity_minutes} minutes Â· {run.result.schedule.timezone_name}</p>
                    <p className={quiet}>Based on working hours and your saved AURA schedule. Check external calendar availability before scheduling these tasks.</p>
                    <ul className="mt-2 space-y-1 text-sm">
                      {run.result.schedule.entries.map((entry) => (
                        <li key={`${entry.task_id}-${entry.segment_index}`}>
                          {new Date(entry.start_at).toLocaleTimeString([], { timeZone: run.result.schedule?.timezone_name, hour: "numeric", minute: "2-digit" })}
                          {" Â· "}{entry.title} ({entry.duration_minutes} min)
                        </li>
                      ))}
                      {run.result.schedule.unscheduled.map((task) => (
                        <li key={task.task_id}>{task.title} Â· {task.remaining_minutes} min still to schedule</li>
                      ))}
                    </ul>
                    <Link href="/planner/daily" className="mt-2 inline-block text-sm underline">Open daily planner</Link>
                  </div>
                )}
                {run.result.comparison && (
                  <div className="my-4 text-sm">
                    <h3 className="font-semibold">Changes since the earlier plan</h3>
                    <p>{run.result.comparison.previous_task_count} previous tasks Â· {run.result.comparison.proposed_task_count} proposed tasks</p>
                    <p>Estimated work change: {run.result.comparison.estimated_minutes_change} min Â· Overdue existing tasks: {run.result.comparison.overdue_task_count}</p>
                  </div>
                )}
                {run.result.simulation && (
                  <ul className="my-4 list-disc space-y-1 pl-5 text-sm">
                    {[
                      `Scheduled minutes: ${run.result.simulation.baseline.scheduled_minutes} before, ${run.result.simulation.simulated.scheduled_minutes} in the scenario`,
                      ...run.result.simulation.explanations,
                      ...run.result.simulation.potential_deadline_conflicts,
                    ].map((line, index) => <li key={index}>{line}</li>)}
                  </ul>
                )}
                <div className="flex flex-wrap gap-2">
                  {run.goal_id && run.result.plan && <Button disabled={busy} variant="outline" onClick={() => previewAlternative()}>Preview a revised plan</Button>}
                  {run.status === "awaiting_approval" && <>
                    <Button disabled={busy} className={primary} onClick={() => decide("approve")}>Approve and create tasks</Button>
                    <Button disabled={busy} variant="outline" onClick={() => decide("pause")}>Pause</Button>
                    <Button disabled={busy} variant="outline" onClick={() => decide("reject")}>Reject</Button>
                  </>}
                  {run.status === "paused" && <>
                    <Button disabled={busy} onClick={() => decide("resume")}>Resume review</Button>
                    <Button disabled={busy} variant="outline" onClick={() => decide("cancel")}>Cancel workflow</Button>
                  </>}
                </div>
                {run.status === "completed" && run.result.evidence?.status === "verified" && (
                  <p className="my-4 text-sm">Verified {run.result.evidence.task_ids.length} created tasks. <Link className="underline" href="/tasks">View tasks</Link></p>
                )}
                {run.status === "completed" && run.result.evidence?.status === "verified" && (
                  <Button disabled={busy} variant="outline" onClick={() => decide("undo")}>Remove created tasks</Button>
                )}
                <h3 className="mt-6 font-semibold">Activity timeline</h3>
                <ol className="mt-2 grid gap-2 border-s border-slate-300 pl-4 text-sm dark:border-slate-600">
                  {run.result.trace.map((event, index) => (
                    <li key={index}>
                      <span className="capitalize">{event.agent} Â· {event.outcome.replaceAll("_", " ")}</span>
                      <time dateTime={event.at} className={`ms-2 ${quiet}`}>{new Date(event.at).toLocaleString()}</time>
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
