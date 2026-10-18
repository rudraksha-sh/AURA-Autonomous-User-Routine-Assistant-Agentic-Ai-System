"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, Circle, Plus, Trash2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { getGoals } from "@/services/goals";
import { ApiError } from "@/services/auth";
import { clearAccessToken } from "@/services/auth-storage";
import { createTask, deleteTask, getTasks, TaskApiError, updateTask } from "@/services/tasks";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

export default function TasksPage() {
  const router = useRouter();
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [title, setTitle] = React.useState("");
  const [deadline, setDeadline] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("medium");
  const [editingTaskId, setEditingTaskId] = React.useState<number | null>(null);
  const [editingTitle, setEditingTitle] = React.useState("");
  const [editingDescription, setEditingDescription] = React.useState("");
  const [editingDeadline, setEditingDeadline] = React.useState("");
  const [editingPriority, setEditingPriority] = React.useState("medium");
  const [goalId, setGoalId] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
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
      const [goalData, taskData] = await Promise.all([getGoals(), getTasks()]);
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

  React.useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function addTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !goalId) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createTask(Number(goalId), {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        deadline: deadline ? new Date(`${deadline}T12:00:00`).toISOString() : null,
      });
      setTasks((current) => [...current, created]);
      setTitle("");
      setDeadline("");
      setDescription("");
      setPriority("medium");
    } catch (err) {
      reportError(err, "Unable to create task.");
    } finally { setSaving(false); }
  }

  async function toggleTask(task: Task) {
    const status = task.status.toLowerCase() === "completed" ? "pending" : "completed";
    try {
      const updated = await updateTask(task.id, { status });
      setTasks((current) => current.map((item) => item.id === task.id ? updated : item));
    } catch (err) { reportError(err, "Unable to update task."); }
  }

  async function removeTask(task: Task) {
    if (!window.confirm(`Delete "${task.title}"? This cannot be undone.`)) return;
    try {
      await deleteTask(task.id);
      setTasks((current) => current.filter((item) => item.id !== task.id));
    } catch (err) { reportError(err, "Unable to delete task."); }
  }

  async function saveTask(task: Task) {
    if (!editingTitle.trim()) return;
    try {
      const updated = await updateTask(task.id, {
        title: editingTitle.trim(),
        description: editingDescription.trim() || null,
        priority: editingPriority,
        deadline: editingDeadline ? new Date(`${editingDeadline}T12:00:00`).toISOString() : null,
      });
      setTasks((current) => current.map((item) => item.id === task.id ? updated : item));
      setEditingTaskId(null);
      setEditingTitle("");
    } catch (err) { reportError(err, "Unable to edit task."); }
  }

  return <div className="min-h-screen bg-slate-50 md:flex"><Sidebar /><div className="min-w-0 flex-1"><Header userName="User" title="Tasks" /><main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
    <div><h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Tasks</h2><p className="mt-2 text-sm text-slate-500 sm:text-base">Manage the next steps attached to your goals.</p></div>
    {error && <div role="alert" className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button type="button" onClick={() => void load()} className="font-semibold underline">Retry</button></div>}
    <form onSubmit={addTask} className="mt-8 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-3"><div className="sm:col-span-2 lg:col-span-1"><label htmlFor="task-title" className="sr-only">Task title</label><input id="task-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Add a task" maxLength={255} required className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"/></div><label className="sr-only" htmlFor="task-description">Description</label><input id="task-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description (optional)" className="rounded-xl border border-slate-300 px-4 py-3 text-sm"/><label className="sr-only" htmlFor="task-deadline">Due date</label><input id="task-deadline" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="rounded-xl border border-slate-300 px-3 py-3 text-sm"/><label className="sr-only" htmlFor="task-priority">Priority</label><select id="task-priority" value={priority} onChange={(event) => setPriority(event.target.value)} className="rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm"><option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option></select><label className="sr-only" htmlFor="task-goal">Goal</label><select id="task-goal" value={goalId} onChange={(event) => setGoalId(event.target.value)} disabled={!goals.length} required className="rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm"><option value="" disabled>Select a goal</option>{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select><button disabled={saving || !goals.length} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"><Plus aria-hidden="true" className="size-4"/>{saving ? "Adding..." : "Add task"}</button></form>
    {loading ? <div role="status" className="mt-6 animate-pulse rounded-2xl bg-slate-200 p-12 text-center text-sm text-slate-500">Loading your tasks...</div> : tasks.length === 0 ? <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center"><p className="font-semibold text-slate-800">No tasks yet</p><p className="mt-1 text-sm text-slate-500">Add a task above and link it to one of your goals.</p></div> : <section aria-label="Your tasks" className="mt-6 space-y-3">{tasks.map((task) => <article key={task.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-3"><button type="button" onClick={() => void toggleTask(task)} aria-label={`${task.status === "completed" ? "Mark incomplete" : "Complete"}: ${task.title}`} className="flex size-10 shrink-0 items-center justify-center rounded-xl text-blue-600 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">{task.status.toLowerCase() === "completed" ? <Check aria-hidden="true"/> : <Circle aria-hidden="true"/>}</button><div className="min-w-0 flex-1"><p className={`break-words text-sm font-semibold ${task.status.toLowerCase() === "completed" ? "text-slate-400 line-through" : "text-slate-900"}`}>{task.title}</p><p className="mt-1 text-xs text-slate-500">{goals.find((goal) => goal.id === task.goal_id)?.title ?? "Goal"} · {task.priority} priority{task.deadline ? ` · Due ${new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(task.deadline))}` : ""}</p>{task.description && <p className="mt-1 text-sm text-slate-500">{task.description}</p>}</div><button type="button" onClick={() => { const open = editingTaskId !== task.id; setEditingTaskId(open ? task.id : null); setEditingTitle(task.title); setEditingDescription(task.description ?? ""); setEditingPriority(task.priority); setEditingDeadline(task.deadline ? new Date(task.deadline).toLocaleDateString("en-CA") : ""); }} aria-label={`Edit ${task.title}`} className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Edit</button><button type="button" onClick={() => void removeTask(task)} aria-label={`Delete ${task.title}`} className="flex size-10 items-center justify-center rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><Trash2 aria-hidden="true" className="size-4"/></button></div>{editingTaskId === task.id && <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); void saveTask(task); }}><label className="sr-only" htmlFor={`edit-task-${task.id}`}>Task title</label><input id={`edit-task-${task.id}`} autoFocus value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} maxLength={255} required placeholder="Task title" className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"/><label className="sr-only" htmlFor={`edit-description-${task.id}`}>Description</label><input id={`edit-description-${task.id}`} value={editingDescription} onChange={(event) => setEditingDescription(event.target.value)} placeholder="Description (optional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm"/><label className="sr-only" htmlFor={`edit-deadline-${task.id}`}>Due date</label><input id={`edit-deadline-${task.id}`} type="date" value={editingDeadline} onChange={(event) => setEditingDeadline(event.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"/><label className="sr-only" htmlFor={`edit-priority-${task.id}`}>Priority</label><select id={`edit-priority-${task.id}`} value={editingPriority} onChange={(event) => setEditingPriority(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option></select><div className="flex gap-2 sm:col-span-2"><button type="submit" className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">Save changes</button><button type="button" onClick={() => setEditingTaskId(null)} className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100">Cancel</button></div></form>}</article>)}</section>}
  </main></div></div>;
}
