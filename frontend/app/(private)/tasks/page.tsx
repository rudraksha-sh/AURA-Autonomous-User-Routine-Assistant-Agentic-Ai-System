"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, Circle, LayoutGrid, List, Plus, Search, Trash2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { TaskBoard } from "@/components/tasks/TaskBoard";
import { TaskDetailDrawer } from "@/components/tasks/TaskDetailDrawer";
import { ApiError, getMe } from "@/services/auth";
import { clearAccessToken } from "@/services/auth-storage";
import { getGoals } from "@/services/goals";
import { createTask, deleteTask, getTasks, runBulkTaskAction, TaskApiError, updateTask } from "@/services/tasks";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";
import { getTaskScore } from "@/lib/task-score";

type View = "list" | "board";
type Sort = "manual" | "score" | "deadline" | "priority";

function taskDate(task: Task) {
  if (!task.deadline) return "";
  const value = new Date(task.deadline);
  return Number.isNaN(value.getTime()) ? "" : `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function sortTasks(tasks: Task[], goals: Goal[], sort: Sort) {
  const priorityValue = (task: Task) => task.priority === "high" ? 3 : task.priority === "medium" ? 2 : 1;
  return [...tasks].sort((left, right) => {
    if (sort === "score") return getTaskScore(right, goals.find((goal) => goal.id === right.goal_id)) - getTaskScore(left, goals.find((goal) => goal.id === left.goal_id));
    if (sort === "deadline") return (left.deadline ? Date.parse(left.deadline) : Number.POSITIVE_INFINITY) - (right.deadline ? Date.parse(right.deadline) : Number.POSITIVE_INFINITY);
    if (sort === "priority") return priorityValue(right) - priorityValue(left);
    return left.position - right.position || left.id - right.id;
  });
}

export default function TasksPage() {
  const router = useRouter();
  const [userId, setUserId] = React.useState<number | null>(null);
  const [userName, setUserName] = React.useState("User");
  const [view, setView] = React.useState<View>("list");
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [selectedIds, setSelectedIds] = React.useState<Set<number>>(new Set());
  const [drawerTask, setDrawerTask] = React.useState<Task | null>(null);
  const [title, setTitle] = React.useState("");
  const [deadline, setDeadline] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("medium");
  const [goalId, setGoalId] = React.useState("");
  const [goalFilter, setGoalFilter] = React.useState("all");
  const [priorityFilter, setPriorityFilter] = React.useState("all");
  const [fromDate, setFromDate] = React.useState("");
  const [throughDate, setThroughDate] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [sort, setSort] = React.useState<Sort>("manual");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [bulkBusy, setBulkBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function reportError(err: unknown, fallback: string) {
    if (err instanceof TaskApiError && err.status === 401) {
      clearAccessToken();
      router.replace("/login");
      return;
    }
    setError(err instanceof Error ? err.message : fallback);
  }

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [currentUser, goalData, taskData] = await Promise.all([getMe(), getGoals(), getTasks()]);
      let savedView: string | null = null;
      try { savedView = window.localStorage.getItem(`aura_task_view_${currentUser.id}`); } catch { /* Keep the list view when storage is unavailable. */ }
      setView(savedView === "board" ? "board" : "list");
      setUserId(currentUser.id);
      setUserName(currentUser.name);
      setGoals(goalData);
      setTasks(taskData);
      setGoalId((current) => current || String(goalData[0]?.id ?? ""));
    } catch (err) {
      if ((err instanceof TaskApiError && err.status === 401) || (err instanceof ApiError && err.status === 401)) {
        clearAccessToken();
        router.replace("/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  React.useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  React.useEffect(() => {
    if (userId !== null) {
      try { window.localStorage.setItem(`aura_task_view_${userId}`, view); } catch { /* The preference remains available for this visit. */ }
    }
  }, [userId, view]);

  async function addTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !goalId) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createTask(Number(goalId), { title: title.trim(), description: description.trim() || null, priority, deadline: deadline ? new Date(`${deadline}T12:00:00`).toISOString() : null });
      setTasks((current) => [...current, created]);
      setTitle(""); setDeadline(""); setDescription(""); setPriority("medium");
    } catch (err) { reportError(err, "Unable to create task."); }
    finally { setSaving(false); }
  }

  async function toggleTask(task: Task) {
    const snapshot = tasks;
    const status = task.status === "completed" ? "pending" : "completed";
    setTasks((current) => current.map((item) => item.id === task.id ? { ...item, status } : item));
    try {
      const updated = await updateTask(task.id, { status });
      setTasks((current) => current.map((item) => item.id === task.id ? updated : item));
    } catch (err) { setTasks(snapshot); reportError(err, "Unable to update task."); }
  }

  async function removeTask(task: Task) {
    if (!window.confirm(`Delete “${task.title}”? This cannot be undone.`)) return;
    const snapshot = tasks;
    setTasks((current) => current.filter((item) => item.id !== task.id));
    try {
      await deleteTask(task.id);
      if (drawerTask?.id === task.id) setDrawerTask(null);
      setSelectedIds((current) => { const next = new Set(current); next.delete(task.id); return next; });
    } catch (err) { setTasks(snapshot); reportError(err, "Unable to delete task."); }
  }

  async function bulkAction(action: "complete" | "delete") {
    const ids = [...selectedIds].filter((id) => visibleTasks.some((task) => task.id === id));
    if (!ids.length || bulkBusy) return;
    if (action === "delete" && !window.confirm(`Delete ${ids.length} selected task${ids.length === 1 ? "" : "s"}? This cannot be undone.`)) return;
    const snapshot = tasks;
    setBulkBusy(true);
    setError(null);
    setTasks((current) => action === "delete" ? current.filter((task) => !selectedIds.has(task.id)) : current.map((task) => selectedIds.has(task.id) ? { ...task, status: "completed" } : task));
    setSelectedIds(new Set());
    try {
      const result = await runBulkTaskAction(ids, action);
      if (action === "complete") {
        const byId = new Map(result.tasks.map((task) => [task.id, task]));
        setTasks((current) => current.map((task) => byId.get(task.id) ?? task));
      }
    } catch (err) { setTasks(snapshot); reportError(err, "Unable to apply bulk task action."); }
    finally { setBulkBusy(false); }
  }

  function selectTask(taskId: number, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(taskId);
      else next.delete(taskId);
      return next;
    });
  }

  async function reorderBoard(orders: Array<{ status: string; ids: number[] }>) {
    const snapshot = tasks;
    const changes = orders.flatMap(({ status, ids }) => ids.map((id, index) => ({ task: snapshot.find((item) => item.id === id), status, position: index + 1 }))).filter((item): item is { task: Task; status: string; position: number } => Boolean(item.task));
    if (!changes.length) return;
    setTasks((current) => current.map((task) => {
      const changed = changes.find((item) => item.task.id === task.id);
      return changed ? { ...task, status: changed.status, position: changed.position } : task;
    }));
    setError(null);
    try {
      const updated = await Promise.all(changes.map(({ task, status, position }) => updateTask(task.id, { status, position })));
      const byId = new Map(updated.map((task) => [task.id, task]));
      setTasks((current) => current.map((task) => byId.get(task.id) ?? task));
    } catch (err) {
      await Promise.allSettled(changes.map(({ task }) => updateTask(task.id, { status: task.status, position: task.position })));
      setTasks(snapshot);
      reportError(err, "Unable to move task. Your board was restored.");
    }
  }

  const query = search.trim().toLowerCase();
  const visibleTasks = sortTasks(tasks.filter((task) => {
    if (goalFilter !== "all" && task.goal_id !== Number(goalFilter)) return false;
    if (priorityFilter !== "all" && task.priority !== priorityFilter) return false;
    const due = taskDate(task);
    if (fromDate && (!due || due < fromDate)) return false;
    if (throughDate && (!due || due > throughDate)) return false;
    if (query && !`${task.title} ${task.description ?? ""} ${task.notes ?? ""}`.toLowerCase().includes(query)) return false;
    return true;
  }), goals, sort);
  const allVisibleSelected = visibleTasks.length > 0 && visibleTasks.every((task) => selectedIds.has(task.id));
  const visibleSelectedCount = visibleTasks.filter((task) => selectedIds.has(task.id)).length;
  const canReorder = view === "board" && sort === "manual" && goalFilter === "all" && priorityFilter === "all" && !fromDate && !throughDate && !search.trim();

  const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2";
  return <div className="min-h-screen bg-slate-50 md:flex"><Sidebar /><div className="min-w-0 flex-1"><Header userName={userName} title="Tasks" /><main className="mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Tasks</h1><p className="mt-2 text-sm text-slate-500 sm:text-base">Manage the next steps attached to your goals.</p></div><div role="group" aria-label="Task view" className="inline-flex self-start rounded-xl border border-slate-200 bg-white p-1 shadow-sm sm:self-auto"><button type="button" aria-pressed={view === "list"} onClick={() => setView("list")} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${view === "list" ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"} ${focusRing}`}><List aria-hidden="true" className="size-4" />List</button><button type="button" aria-pressed={view === "board"} onClick={() => setView("board")} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${view === "board" ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"} ${focusRing}`}><LayoutGrid aria-hidden="true" className="size-4" />Board</button></div></div>

    {error && <div role="alert" className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button type="button" onClick={() => void load()} className={`font-semibold underline ${focusRing}`}>Retry</button></div>}

    <form onSubmit={(event) => void addTask(event)} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 sm:p-5 lg:grid-cols-6">
      <div className="sm:col-span-2 lg:col-span-2"><label htmlFor="task-title" className="sr-only">Task title</label><input id="task-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Add a task" maxLength={255} required className={`w-full rounded-xl border border-slate-300 px-4 py-3 text-sm ${focusRing}`} /></div>
      <div className="sm:col-span-2 lg:col-span-2"><label htmlFor="task-description" className="sr-only">Description</label><input id="task-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description (optional)" className={`w-full rounded-xl border border-slate-300 px-4 py-3 text-sm ${focusRing}`} /></div>
      <label className="sr-only" htmlFor="task-deadline">Due date</label><input id="task-deadline" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} className={`rounded-xl border border-slate-300 px-3 py-3 text-sm ${focusRing}`} />
      <label className="sr-only" htmlFor="task-priority">Priority</label><select id="task-priority" value={priority} onChange={(event) => setPriority(event.target.value)} className={`rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm ${focusRing}`}><option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option></select>
      <label className="sr-only" htmlFor="task-goal">Goal</label><select id="task-goal" value={goalId} onChange={(event) => setGoalId(event.target.value)} disabled={!goals.length} required className={`rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm sm:col-span-2 lg:col-span-4 ${focusRing}`}><option value="" disabled>Select a goal</option>{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select>
      <button disabled={saving || !goals.length} className={`inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 sm:col-span-2 lg:col-span-2 ${focusRing}`}><Plus aria-hidden="true" className="size-4" />{saving ? "Adding…" : "Add task"}</button>
    </form>

    <section aria-label="Task filters" className="mt-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
      <div className="relative sm:col-span-2 lg:col-span-2"><Search aria-hidden="true" className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><label htmlFor="task-search" className="sr-only">Search tasks</label><input id="task-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search tasks" className={`w-full rounded-xl border border-slate-300 py-2.5 pl-9 pr-3 text-sm ${focusRing}`} /></div>
      <label className="sr-only" htmlFor="filter-goal">Filter by goal</label><select id="filter-goal" value={goalFilter} onChange={(event) => setGoalFilter(event.target.value)} className={`rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm ${focusRing}`}><option value="all">All goals</option>{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select>
      <label className="sr-only" htmlFor="filter-priority">Filter by priority</label><select id="filter-priority" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} className={`rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm ${focusRing}`}><option value="all">All priorities</option><option value="high">High priority</option><option value="medium">Medium priority</option><option value="low">Low priority</option></select>
      <label className="sr-only" htmlFor="filter-from">Due from</label><input id="filter-from" aria-label="Due from" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} className={`rounded-xl border border-slate-300 px-2 py-2.5 text-sm ${focusRing}`} />
      <label className="sr-only" htmlFor="filter-through">Due through</label><input id="filter-through" aria-label="Due through" type="date" value={throughDate} onChange={(event) => setThroughDate(event.target.value)} className={`rounded-xl border border-slate-300 px-2 py-2.5 text-sm ${focusRing}`} />
      <label className="sr-only" htmlFor="task-sort">Sort tasks</label><select id="task-sort" value={sort} onChange={(event) => setSort(event.target.value as Sort)} className={`rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm sm:col-span-2 lg:col-span-2 ${focusRing}`}><option value="manual">Manual order</option><option value="score">Suggested score</option><option value="deadline">Deadline</option><option value="priority">Priority</option></select>
    </section>

    <section aria-label="Bulk task actions" className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-3">
      <label className="inline-flex items-center gap-2 px-2 py-1 text-sm font-medium text-slate-700"><input type="checkbox" checked={allVisibleSelected} onChange={(event) => { const checked = event.target.checked; setSelectedIds((current) => { const next = new Set(current); visibleTasks.forEach((task) => { if (checked) next.add(task.id); else next.delete(task.id); }); return next; }); }} className="size-4 rounded border-slate-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-600" />Select visible</label>
      <span className="text-xs text-slate-500">{visibleTasks.length} task{visibleTasks.length === 1 ? "" : "s"}</span>
      {visibleSelectedCount > 0 && <><span aria-live="polite" className="ml-auto text-xs font-medium text-slate-600">{visibleSelectedCount} selected</span><button type="button" disabled={bulkBusy} onClick={() => void bulkAction("complete")} className={`inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 ${focusRing}`}><Check aria-hidden="true" className="size-3.5" />Complete</button><button type="button" disabled={bulkBusy} onClick={() => void bulkAction("delete")} className={`inline-flex items-center gap-2 rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50 ${focusRing}`}><Trash2 aria-hidden="true" className="size-3.5" />Delete</button></>}
    </section>

    {loading ? <div role="status" aria-label="Loading tasks" className="mt-5 grid gap-3 md:grid-cols-2"><span className="sr-only">Loading your tasks…</span>{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-2xl bg-slate-200" />)}</div> : visibleTasks.length === 0 ? <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center sm:p-10"><p className="font-semibold text-slate-800">{tasks.length === 0 ? "No tasks yet" : "No tasks match these filters"}</p><p className="mt-1 text-sm text-slate-500">{tasks.length === 0 ? "Add a task above and link it to one of your goals." : "Try a different search or clear a filter."}</p>{tasks.length === 0 && !goals.length && <Link href="/goals" className={`mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white ${focusRing}`}>Create a goal <Plus aria-hidden="true" className="size-4" /></Link>}</div> : view === "board" ? <div className="mt-5">{!canReorder && <p className="mb-3 text-xs text-slate-500">Clear filters and choose Manual order to drag tasks between columns.</p>}<TaskBoard tasks={visibleTasks} goals={goals} selectedIds={selectedIds} reorderingEnabled={canReorder} onSelect={selectTask} onToggle={(task) => void toggleTask(task)} onOpen={setDrawerTask} onDelete={(task) => void removeTask(task)} onReorder={(orders) => void reorderBoard(orders)} /></div> : <section aria-label="Your tasks" className="mt-5 space-y-3">{visibleTasks.map((task) => <article key={task.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-start gap-3"><input type="checkbox" checked={selectedIds.has(task.id)} onChange={(event) => selectTask(task.id, event.target.checked)} aria-label={`Select ${task.title}`} className="mt-1 size-4 rounded border-slate-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-600" /><button type="button" onClick={() => void toggleTask(task)} aria-label={`${task.status === "completed" ? "Reopen" : "Complete"} ${task.title}`} className={`flex size-9 shrink-0 items-center justify-center rounded-xl text-blue-600 hover:bg-blue-50 ${focusRing}`}>{task.status === "completed" ? <Check aria-hidden="true" /> : <Circle aria-hidden="true" />}</button><button type="button" onClick={() => setDrawerTask(task)} className={`min-w-0 flex-1 text-left ${focusRing}`}><span className={`block break-words text-sm font-semibold ${task.status === "completed" ? "text-slate-400 line-through" : "text-slate-900"}`}>{task.title}</span><span className="mt-1 block text-xs text-slate-500">{goals.find((goal) => goal.id === task.goal_id)?.title ?? "Goal"} · {task.priority} priority · {task.status.replace("_", " ")}{task.deadline ? ` · Due ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(task.deadline))}` : ""}{task.estimated_minutes ? ` · ${task.estimated_minutes} min` : ""}</span>{task.description && <span className="mt-1 block text-sm text-slate-500">{task.description}</span>}</button><button type="button" onClick={() => void removeTask(task)} aria-label={`Delete ${task.title}`} className={`flex size-9 shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-700 ${focusRing}`}><Trash2 aria-hidden="true" className="size-4" /></button></div></article>)}</section>}
  </main></div>{drawerTask && <TaskDetailDrawer task={drawerTask} onClose={() => setDrawerTask(null)} onSaved={(updated) => { setTasks((current) => current.map((task) => task.id === updated.id ? updated : task)); setDrawerTask(updated); }} />}</div>;
}
