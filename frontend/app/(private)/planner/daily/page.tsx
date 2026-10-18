"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, CalendarDays, Check, Clock3, Loader2, RefreshCw, Save, Settings2, Trash2, FlaskConical } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import {
  approveDailySchedule,
  getDailySchedule,
  getPlanningPreferences,
  PlannerApiError,
  previewDailySchedule,
  savePlanningPreferences,
  simulateDailySchedule,
} from "@/services/planner";
import type { DailySchedule, PlanningPreferences, ScheduleEntryProposal, SchedulePreview, WhatIfResult } from "@/types/planner";

const DEFAULT_PREFERENCES: PlanningPreferences = {
  timezone_name: "UTC",
  workday_start: "09:00",
  workday_end: "17:00",
  preferred_session_minutes: 50,
  break_minutes: 10,
  daily_capacity_minutes: 360,
};

function localDateString(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function dateTimeParts(value: Date, zone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

function zonedTimeToIso(day: string, clock: string, zone: string): string {
  const [year, month, date] = day.split("-").map(Number);
  const [hour, minute] = clock.split(":").map(Number);
  const target = Date.UTC(year, month - 1, date, hour, minute);
  let guess = target;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = dateTimeParts(new Date(guess), zone);
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute));
    guess += target - represented;
  }
  return new Date(guess).toISOString();
}

function timeInZone(value: string, zone: string) {
  const parts = dateTimeParts(new Date(value), zone);
  return `${parts.hour}:${parts.minute}`;
}

function displayTime(value: string, zone: string) {
  return new Intl.DateTimeFormat(undefined, { timeZone: zone, hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export default function DailyPlannerPage() {
  const [targetDate, setTargetDate] = React.useState(localDateString());
  const [preferences, setPreferences] = React.useState(DEFAULT_PREFERENCES);
  const [entries, setEntries] = React.useState<ScheduleEntryProposal[]>([]);
  const [unscheduled, setUnscheduled] = React.useState<SchedulePreview["unscheduled"]>([]);
  const [savedSchedule, setSavedSchedule] = React.useState<DailySchedule | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [building, setBuilding] = React.useState(false);
  const [savingSettings, setSavingSettings] = React.useState(false);
  const [savingSchedule, setSavingSchedule] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = React.useState<string | null>(null);
  const [scenarioCapacity, setScenarioCapacity] = React.useState("");
  const [scenarioTaskTitle, setScenarioTaskTitle] = React.useState("");
  const [scenarioTaskMinutes, setScenarioTaskMinutes] = React.useState("45");
  const [blockedStart, setBlockedStart] = React.useState("");
  const [blockedMinutes, setBlockedMinutes] = React.useState("60");
  const [simulation, setSimulation] = React.useState<WhatIfResult | null>(null);
  const [simulating, setSimulating] = React.useState(false);
  const [simulationError, setSimulationError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    Promise.all([getPlanningPreferences(), getDailySchedule(targetDate)]).then(([prefs, schedule]) => {
      if (!active) return;
      const normalized = { ...prefs, workday_start: prefs.workday_start.slice(0, 5), workday_end: prefs.workday_end.slice(0, 5) };
      setPreferences(normalized);
      setSavedSchedule(schedule);
      setEntries(schedule?.entries ?? []);
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : "Unable to load your schedule settings.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [targetDate]);

  function updateEntry(index: number, change: Partial<ScheduleEntryProposal>) {
    setEntries((current) => current.map((entry, itemIndex) => itemIndex === index ? { ...entry, ...change } : entry));
    setSavedSchedule(null);
    setIdempotencyKey(null);
  }

  async function generate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBuilding(true); setError(null); setNotice(null); setIdempotencyKey(null);
    try {
      const preview = await previewDailySchedule(targetDate);
      setEntries(preview.entries);
      setUnscheduled(preview.unscheduled);
      setSavedSchedule(null);
      if (!preview.entries.length) setNotice("There are no eligible tasks to schedule for this day.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to build a schedule.");
    } finally { setBuilding(false); }
  }

  async function savePreferences(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingSettings(true); setError(null); setNotice(null);
    try {
      const updated = await savePlanningPreferences(preferences);
      setPreferences({ ...updated, workday_start: updated.workday_start.slice(0, 5), workday_end: updated.workday_end.slice(0, 5) });
      setNotice("Planning preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save preferences.");
    } finally { setSavingSettings(false); }
  }

  async function approve() {
    if (!entries.length) return;
    if (!window.confirm(`Approve this ${entries.length}-session schedule for ${targetDate}?`)) return;
    const key = idempotencyKey ?? crypto.randomUUID();
    setIdempotencyKey(key); setSavingSchedule(true); setError(null); setNotice(null);
    try {
      const schedule = await approveDailySchedule(targetDate, key, entries);
      setSavedSchedule(schedule);
      setEntries(schedule.entries);
      setNotice("Schedule approved and saved.");
    } catch (err) {
      if (err instanceof PlannerApiError && err.status === 401) return;
      setError(err instanceof Error ? err.message : "Unable to save the schedule. Retry to safely check the same approval.");
    } finally { setSavingSchedule(false); }
  }

  async function runSimulation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSimulating(true); setSimulationError(null); setSimulation(null);
    const request = {
      target_date: targetDate,
      ...(scenarioCapacity ? { capacity_minutes: Number(scenarioCapacity) } : {}),
      ...(scenarioTaskTitle.trim() ? { proposed_task: { title: scenarioTaskTitle.trim(), estimated_minutes: Number(scenarioTaskMinutes), priority: "high" as const } } : {}),
      ...(blockedStart ? { unavailable_start_at: zonedTimeToIso(targetDate, blockedStart, preferences.timezone_name), unavailable_minutes: Number(blockedMinutes) } : {}),
    };
    try {
      setSimulation(await simulateDailySchedule(request));
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : "Unable to simulate this scenario.");
    } finally { setSimulating(false); }
  }

  const scheduledMinutes = entries.reduce((total, entry) => total + entry.duration_minutes, 0);

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Header userName="User" title="Daily Planner" />
        <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <Link href="/planner" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900"><ArrowLeft aria-hidden="true" className="size-4" />Goal planner</Link>
          <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold tracking-tight text-slate-900">Plan a realistic workday</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">A deterministic schedule from your open tasks, priority, deadlines, estimates, and available time. No AI service is used.</p></div><span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700"><CalendarDays aria-hidden="true" className="size-4" />{savedSchedule ? "Approved schedule" : "Draft schedule"}</span></div>
            {error && <div role="alert" className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button type="button" onClick={() => { setError(null); setLoading(true); void Promise.all([getPlanningPreferences(), getDailySchedule(targetDate)]).then(([prefs, schedule]) => { setPreferences({ ...prefs, workday_start: prefs.workday_start.slice(0, 5), workday_end: prefs.workday_end.slice(0, 5) }); setSavedSchedule(schedule); setEntries(schedule?.entries ?? []); }).catch((err: unknown) => setError(err instanceof Error ? err.message : "Retry failed.")).finally(() => setLoading(false)); }} className="font-semibold underline">Retry</button></div>}
            {notice && <p role="status" className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"><Check aria-hidden="true" className="size-4" />{notice}</p>}

            <details className="mt-6 rounded-xl border border-slate-200 p-4" open>
              <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold text-slate-800"><Settings2 aria-hidden="true" className="size-4" />Working hours and planning preferences</summary>
              <form onSubmit={savePreferences} className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div><label htmlFor="planning-zone" className="block text-xs font-medium text-slate-600">Time zone (IANA)</label><input id="planning-zone" value={preferences.timezone_name} onChange={(event) => setPreferences((current) => ({ ...current, timezone_name: event.target.value }))} required maxLength={64} placeholder="America/New_York" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="planning-start" className="block text-xs font-medium text-slate-600">Workday starts</label><input id="planning-start" type="time" value={preferences.workday_start} onChange={(event) => setPreferences((current) => ({ ...current, workday_start: event.target.value }))} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="planning-end" className="block text-xs font-medium text-slate-600">Workday ends</label><input id="planning-end" type="time" value={preferences.workday_end} onChange={(event) => setPreferences((current) => ({ ...current, workday_end: event.target.value }))} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="planning-session" className="block text-xs font-medium text-slate-600">Preferred session (minutes)</label><input id="planning-session" type="number" min={15} max={180} value={preferences.preferred_session_minutes} onChange={(event) => setPreferences((current) => ({ ...current, preferred_session_minutes: Number(event.target.value) }))} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="planning-break" className="block text-xs font-medium text-slate-600">Break between sessions (minutes)</label><input id="planning-break" type="number" min={0} max={60} value={preferences.break_minutes} onChange={(event) => setPreferences((current) => ({ ...current, break_minutes: Number(event.target.value) }))} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="planning-capacity" className="block text-xs font-medium text-slate-600">Daily work capacity (minutes)</label><input id="planning-capacity" type="number" min={30} max={720} value={preferences.daily_capacity_minutes} onChange={(event) => setPreferences((current) => ({ ...current, daily_capacity_minutes: Number(event.target.value) }))} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <button type="submit" disabled={savingSettings || loading} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 sm:col-span-2 lg:col-span-3">{savingSettings ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <Save aria-hidden="true" className="size-4" />}{savingSettings ? "Saving…" : "Save preferences"}</button>
              </form>
            </details>

            <details className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
              <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold text-indigo-900"><FlaskConical aria-hidden="true" className="size-4" />What-if schedule simulator</summary>
              <p className="mt-2 text-sm leading-6 text-slate-600">Preview changes against your current tasks. Scenarios are read-only and do not change tasks or saved schedules.</p>
              <form onSubmit={runSimulation} className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div><label htmlFor="scenario-capacity" className="block text-xs font-medium text-slate-600">Reduced capacity (optional, minutes)</label><input id="scenario-capacity" type="number" min={30} max={preferences.daily_capacity_minutes} value={scenarioCapacity} onChange={(event) => setScenarioCapacity(event.target.value)} placeholder={`Current: ${preferences.daily_capacity_minutes}`} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="scenario-task" className="block text-xs font-medium text-slate-600">Add urgent task (optional)</label><input id="scenario-task" value={scenarioTaskTitle} onChange={(event) => setScenarioTaskTitle(event.target.value)} maxLength={255} placeholder="Task title" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="scenario-task-minutes" className="block text-xs font-medium text-slate-600">Proposed task estimate</label><input id="scenario-task-minutes" type="number" min={1} max={480} value={scenarioTaskMinutes} onChange={(event) => setScenarioTaskMinutes(event.target.value)} disabled={!scenarioTaskTitle.trim()} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100" /></div>
                <div><label htmlFor="scenario-blocked-start" className="block text-xs font-medium text-slate-600">Unavailable slot start (optional)</label><input id="scenario-blocked-start" type="time" value={blockedStart} onChange={(event) => setBlockedStart(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
                <div><label htmlFor="scenario-blocked-minutes" className="block text-xs font-medium text-slate-600">Unavailable slot duration</label><input id="scenario-blocked-minutes" type="number" min={1} max={240} value={blockedMinutes} onChange={(event) => setBlockedMinutes(event.target.value)} disabled={!blockedStart} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100" /></div>
                <button type="submit" disabled={simulating || loading || (!scenarioCapacity && !scenarioTaskTitle.trim() && !blockedStart)} className="inline-flex items-center justify-center gap-2 self-end rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{simulating ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <FlaskConical aria-hidden="true" className="size-4" />}{simulating ? "Simulating…" : "Simulate scenario"}</button>
              </form>
              {simulationError && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{simulationError}</p>}
              {simulation && <section aria-live="polite" className="mt-5 rounded-xl border border-indigo-200 bg-white p-4">
                <h3 className="text-sm font-semibold text-slate-900">Scenario results</h3>
                <p className="mt-1 text-sm text-slate-600">Baseline: {simulation.baseline.scheduled_minutes} minutes scheduled. Scenario: {simulation.simulated.scheduled_minutes} of {simulation.simulated.capacity_minutes} minutes scheduled.</p>
                <ol className="mt-3 space-y-2">{simulation.simulated.entries.map((item, index) => <li key={`${item.task_id ?? "proposed"}-${item.segment_index}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="font-medium text-slate-800">{item.title}{item.is_proposed_task ? " (proposed)" : ""}</span><span className="ml-2 text-slate-500">{displayTime(item.start_at, simulation.simulated.timezone_name)} · {item.duration_minutes} min</span><p className="mt-1 text-xs text-slate-500">{item.explanation}</p></li>)}</ol>
                {simulation.simulated.unscheduled.length > 0 && <div className="mt-4"><h4 className="text-xs font-semibold uppercase tracking-wide text-amber-800">Does not fit</h4><ul className="mt-2 space-y-1 text-sm text-amber-900">{simulation.simulated.unscheduled.map((item, index) => <li key={`${item.task_id ?? "proposed"}-${index}`}>{item.title}{item.is_proposed_task ? " (proposed)" : ""}: {item.remaining_minutes ?? "Unknown"} min remaining.</li>)}</ul></div>}
                {simulation.tasks_no_longer_fit.length > 0 && <p className="mt-3 text-sm text-rose-700">Tasks displaced from the baseline: {simulation.tasks_no_longer_fit.join(", ")}</p>}
                {simulation.potential_deadline_conflicts.length > 0 && <ul className="mt-3 space-y-1 text-sm text-rose-700">{simulation.potential_deadline_conflicts.map((item) => <li key={item}>{item}</li>)}</ul>}
                <p className="mt-3 text-xs text-slate-500">{simulation.explanations.join(" ")}</p>
              </section>}
            </details>

            <form onSubmit={generate} className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end"><div className="flex-1"><label htmlFor="schedule-date" className="block text-sm font-medium text-slate-700">Schedule date</label><input id="schedule-date" type="date" value={targetDate} onChange={(event) => { setTargetDate(event.target.value); setEntries([]); setUnscheduled([]); setSavedSchedule(null); setIdempotencyKey(null); }} required className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm sm:max-w-xs" /></div><button type="submit" disabled={building || loading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{building ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <RefreshCw aria-hidden="true" className="size-4" />}{building ? "Scheduling…" : "Build schedule"}</button></form>

            {loading && <p role="status" className="mt-6 text-sm text-slate-500">Loading your planning data…</p>}
            {!loading && <div className="mt-7">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-900">{savedSchedule ? "Saved timeline" : "Proposed timeline"}</h2><p className="mt-1 text-sm text-slate-500">{scheduledMinutes} minutes scheduled · {preferences.daily_capacity_minutes} minute daily capacity · {preferences.timezone_name}</p></div>{entries.length > 0 && <span className="inline-flex items-center gap-2 text-xs text-slate-500"><Clock3 aria-hidden="true" className="size-4" />Edit start times to rearrange sessions</span>}</div>
              {!entries.length ? <div className="rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">Choose a date and build a schedule from your open tasks.</div> : <ol className="space-y-3">{entries.map((entry, index) => <li key={`${entry.task_id}-${entry.segment_index}-${index}`} className="grid gap-3 rounded-xl border border-slate-200 p-4 sm:grid-cols-[minmax(0,1fr)_9rem_8rem_auto] sm:items-center"><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-900">{entry.title}{entries.filter((item) => item.task_id === entry.task_id).length > 1 ? ` · part ${entry.segment_index}` : ""}</p><p className="mt-1 text-xs text-slate-500">{entry.priority} priority · {displayTime(entry.start_at, preferences.timezone_name)}–{displayTime(new Date(new Date(entry.start_at).getTime() + entry.duration_minutes * 60_000).toISOString(), preferences.timezone_name)}</p><p className="mt-1 text-xs leading-5 text-slate-500">{entry.explanation}</p></div><div><label htmlFor={`schedule-time-${index}`} className="block text-xs font-medium text-slate-600">Start time</label><input id={`schedule-time-${index}`} type="time" value={timeInZone(entry.start_at, preferences.timezone_name)} disabled={Boolean(savedSchedule)} onChange={(event) => updateEntry(index, { start_at: zonedTimeToIso(targetDate, event.target.value, preferences.timezone_name) })} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm disabled:bg-slate-50" /></div><div><label htmlFor={`schedule-duration-${index}`} className="block text-xs font-medium text-slate-600">Duration (minutes)</label><input id={`schedule-duration-${index}`} type="number" min={1} max={180} value={entry.duration_minutes} disabled={Boolean(savedSchedule)} onChange={(event) => updateEntry(index, { duration_minutes: Number(event.target.value) })} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm disabled:bg-slate-50" /></div>{!savedSchedule && <button type="button" onClick={() => setEntries((current) => current.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${entry.title} from schedule`} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700"><Trash2 aria-hidden="true" className="size-4" /></button>}</li>)}</ol>}
              {unscheduled.length > 0 && <section className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4"><h3 className="text-sm font-semibold text-amber-900">Tasks that did not fit</h3><ul className="mt-2 space-y-2">{unscheduled.map((item) => <li key={item.task_id} className="text-sm text-amber-900"><span className="font-medium">{item.title}</span> — {item.remaining_minutes ?? "Unknown"} min remaining. {item.reason}</li>)}</ul></section>}
              {!savedSchedule && entries.length > 0 && <div className="mt-5 flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between"><button type="button" onClick={() => { setEntries([]); setUnscheduled([]); setIdempotencyKey(null); }} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Reject draft</button><button type="button" onClick={approve} disabled={savingSchedule || entries.some((entry) => entry.duration_minutes < 1 || entry.duration_minutes > 180)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{savingSchedule ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <Check aria-hidden="true" className="size-4" />}{savingSchedule ? "Saving approved schedule…" : "Review and approve schedule"}</button></div>}
            </div>}
          </section>
        </main>
      </div>
    </div>
  );
}
