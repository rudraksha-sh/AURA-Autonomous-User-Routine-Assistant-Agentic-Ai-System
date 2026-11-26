"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";

import { ExternalActions } from "@/components/workflows/ExternalActions";
import { AutonomyControls } from "@/components/workflows/AutonomyControls";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { getGoals } from "@/services/goals";
import { PlanningMemory } from "@/components/workflows/PlanningMemory";
import { getReplanSignals, listAutonomyGrants, listWorkflows, recheckWorkflowReceipt, type ReceiptStatus, type ReplanSignals, startReplan, startSimulationWorkflow, startWorkflow, transitionWorkflow, undoWorkflow } from "@/services/planner";
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
  const [includeCalendar, setIncludeCalendar] = useState(false);
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
  const completedId = run?.status === "completed" && run.goal_id ? run.id : undefined;
  const [detection, setDetection] = useState<{ id: string; result: ReplanSignals }>();
  const [receipt, setReceipt] = useState<{ id: string; status: ReceiptStatus }>();
  const signals = detection?.id === completedId ? detection?.result : undefined;

  useEffect(() => {
    if (!completedId) return;
    const controller = new AbortController();
    const check = () => {
      if (document.visibilityState !== "visible") return;
      void getReplanSignals(completedId, controller.signal).then((result) => {
        if (!controller.signal.aborted) setDetection({ id: completedId, result });
      }).catch(() => {});
    };
    check();
    const interval = window.setInterval(check, 30_000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [completedId]);

  async function recheckReceipt(id: string) {
    setError("");
    try {
      const result = await recheckWorkflowReceipt(id);
      setReceipt({ id, status: result.status });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to check the task receipt.");
    }
  }

  function show(item: Workflow) {
    setWorkflows((current) => current.some(({ id }) => id === item.id)
      ? current.map((existing) => existing.id === item.id ? item : existing)
      : [item, ...current]);
    setSelected(item.id);
  }

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = JSON.stringify([goalId, targetDate, grant?.id, includeCalendar]);
    const key = pendingStart?.input === input ? pendingStart.key : crypto.randomUUID();
    setPendingStart({ input, key });
    setBusy(true);
    setError("");
    try {
      show(await startWorkflow(key, Number(goalId), targetDate, grant, includeCalendar));
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
        const capacity = String(values.get("capacity") ?? "");
        const blockedAt = String(values.get("blockedAt") ?? "");
        const blockedMinutes = String(values.get("blockedMinutes") ?? "");
        const taskId = String(values.get("taskId") ?? "");
        const deadline = String(values.get("deadline") ?? "");
        if (Boolean(blockedAt) !== Boolean(blockedMinutes) || Boolean(taskId) !== Boolean(deadline)) {
          throw new Error("Fill in both fields for blocked time or a deadline change.");
        }
        show(await startSimulationWorkflow(crypto.randomUUID(), {
          target_date: String(values.get("day")),
          ...(capacity ? { capacity_minutes: Number(capacity) } : {}),
          ...(blockedAt ? { unavailable_start_at: new Date(blockedAt).toISOString(), unavailable_minutes: Number(blockedMinutes) } : {}),
          ...(taskId ? { deadline_change: { task_id: Number(taskId), deadline: new Date(deadline).toISOString() } } : {}),
        }));
      } else if (run?.goal_id && run.result.schedule) {
        show(await startReplan(crypto.randomUUID(), run.goal_id, run.id, run.result.schedule.target_date, includeCalendar));
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
          <section aria-label="Workflow dashboard" className={`grid gap-2 sm:grid-cols-2 xl:grid-cols-5 ${card}`}>
            {[
              ["Supervisor", "REAL ? rule based routing"],
              ["Context", run?.result.evidence?.context?.status === "ready" ? "PARTIAL ? local index" : "UNAVAILABLE ? pgvector"],
              ["Planner", "REAL ? deterministic proposal"],
              ["Scheduler", run?.result.schedule?.calendar_status === "included" ? "MOCKED ? provider tests only" : "PARTIAL ? local schedule"],
              ["Memory", "REAL ? explicit saved preferences"],
              ["Intelligence", run?.result.capacity ? "REAL ? deterministic metrics" : "PARTIAL ? awaiting plan"],
              ["Simulation", run?.result.simulation ? "REAL ? read only" : "PARTIAL ? start a scenario"],
              ["Replanning", signals?.needs_review ? "REAL ? review required" : "PARTIAL ? 30 second checks"],
              ["Execution", "REAL ? approved local tasks"],
              ["Verification", receipt?.status === "unknown" ? "UNAVAILABLE ? evidence missing" : "REAL ? fingerprint receipt"],
            ].map(([agent, state]) => <div key={agent} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
              <p className="font-semibold">{agent}</p><p>{state}</p>
            </div>)}
          </section>
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
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={includeCalendar} onChange={(event) => setIncludeCalendar(event.target.checked)} />
                      Read Google Calendar availability for this preview
                    </label>
                    <Button disabled={loading || busy || !goalId} type="submit" className={primary}>{grant ? "Create tasks with selected grant" : "Preview plan"}</Button>
                  </form>
                )}
              </section>
              <section className={`order-3 ${card}`}>
                <h2 className="text-lg font-semibold">Simulate schedule changes</h2>
                <form onSubmit={previewAlternative} className="mt-3 grid gap-3 text-sm">
                  <label>Scenario date<input name="day" type="date" className={field} required /></label>
                  <label>Available minutes<input name="capacity" type="number" min={30} max={720} className={field} /></label>
                  <label>Blocked start (device time)<input name="blockedAt" type="datetime-local" className={field} /></label>
                  <label>Blocked minutes<input name="blockedMinutes" type="number" min={1} max={240} className={field} /></label>
                  <label>Task ID for deadline change<input name="taskId" type="number" min={1} className={field} /></label>
                  <label>Proposed deadline (device time)<input name="deadline" type="datetime-local" className={field} /></label>
                  <Button type="submit" variant="outline" disabled={loading || busy}>Run simulation</Button>
                </form>
              </section>
              <ExternalActions goalId={Number(goalId)} field={field} className={`order-4 ${card}`} />
              <PlanningMemory className={`order-4 ${card}`} fieldClassName={field} />
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
                {run.result.evidence?.context && (
                  <details className="my-4 text-sm">
                    <summary className="cursor-pointer font-medium">Context preview</summary>
                    <p className={quiet}>AURA goal</p>
                    {run.result.evidence.context.status === "unavailable" ? (
                      <p className={quiet}>Semantic retrieval was unavailable when this plan was prepared.</p>
                    ) : run.result.evidence.context.sources.length === 0 ? (
                      <p className={quiet}>No related indexed sources were found.</p>
                    ) : (
                      <ul className="space-y-1">
                        {run.result.evidence.context.sources.map((source) => (
                          <li key={`${source.source_id}:${source.chunk}`} title={`Source ${source.source_id}, version ${source.version}`}>
                            <span className="capitalize">{source.kind}</span>{" "}
                            {source.local_id ?? source.source_id.slice(0, 8)} {"·"} chunk {source.chunk + 1}
                          </li>
                        ))}
                      </ul>
                    )}
                  </details>
                )}
                {run.result.plan && (
                  <ol className="my-5 grid gap-3">
                    {run.result.plan.tasks.filter((task) => !run.result.comparison?.preserved_positions?.includes(task.position)).map((task) => (
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
                    {run.result.schedule.calendar_status === "unavailable" && <p role="status">Google Calendar unavailable. This preview uses local availability.</p>}
                    {run.result.schedule.calendar_status === "included" && <p>Google Calendar busy time included.</p>}
                    {!!run.result.schedule.calendar_conflict_task_ids?.length && (
                      <p role="status">Saved tasks overlapping Calendar busy time: {run.result.schedule.calendar_conflict_task_ids.join(", ")}.</p>
                    )}
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
                {run.result.capacity && (
                  <section className="my-4 text-sm">
                    <h3 className="font-semibold">Schedule feasibility</h3>
                    {run.result.capacity.schedule_feasibility_pct === null ? (
                      <p>{run.result.capacity.remaining_minutes} estimated minutes unscheduled.</p>
                    ) : (
                      <p>{run.result.capacity.schedule_feasibility_pct}% of estimated work scheduled. {run.result.capacity.workload_minutes} minutes of work.</p>
                    )}
                    {run.result.capacity.workload_pressure_pct !== null && <p>Workload is {run.result.capacity.workload_pressure_pct}% of available capacity.</p>}
                    <ul>{run.result.capacity.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                  </section>
                )}
                {signals?.needs_review && (
                  <p role="status" className="my-3 text-sm">
                    Review this plan. {signals.changed_task_ids.length} tasks changed, {signals.missing_task_ids.length} are missing,
                    {" "}{signals.overdue_task_ids.length} are overdue, and {signals.conflicting_task_ids.length} have a schedule conflict.
                  </p>
                )}
                {run.result.comparison && (
                  <div className="my-4 text-sm">
                    <h3 className="font-semibold">Changes since the earlier plan</h3>
                    <p>{run.result.comparison.updated_task_ids?.length ?? 0} existing tasks to update, {run.result.comparison.preserved_task_ids?.length ?? 0} preserved, and {run.result.comparison.deleted_task_ids?.length ?? 0} previously deleted.</p>
                    <p>{run.result.comparison.previous_task_count} previous tasks Â· {run.result.comparison.proposed_task_count} proposed tasks</p>
                    <p>Estimated work change: {run.result.comparison.estimated_minutes_change} min Â· Overdue existing tasks: {run.result.comparison.overdue_task_count}</p>
                  </div>
                )}
                {run.result.simulation && (
                  <ul className="my-4 list-disc space-y-1 pl-5 text-sm">
                    {[
                      `Scheduled minutes: ${run.result.simulation.baseline.scheduled_minutes} before, ${run.result.simulation.simulated.scheduled_minutes} in the scenario`,
                      `Unscheduled minutes: ${run.result.simulation.baseline.remaining_minutes ?? 0} before, ${run.result.simulation.simulated.remaining_minutes ?? 0} in the scenario`,
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
                  <div className="my-4 text-sm">
                    <p>Receipt for {run.result.evidence.task_ids.length} tasks. <Link className="underline" href="/tasks">View tasks</Link></p>
                    <Button variant="outline" onClick={() => void recheckReceipt(run.id)}>Recheck receipt</Button>
                    {receipt?.id === run.id && <p role="status" className="capitalize">{receipt.status}</p>}
                  </div>
                )}
                {run.status === "completed" && run.result.evidence?.status === "verified" && !run.result.evidence.reconciled && (
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
