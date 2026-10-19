"use client";

import * as React from "react";
import { Check, Circle, Clock3, Plus, Trash2, X } from "lucide-react";
import { createTaskSubtask, deleteTaskSubtask, getTaskActivity, getTaskSubtasks, updateTask, updateTaskSubtask } from "@/services/tasks";
import type { Task, TaskActivity, TaskSubtask, UpdateTaskInput } from "@/types/task";

function toDateInput(value: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}`;
}

function activitySummary(activity: TaskActivity) {
  const details = activity.details;
  if (activity.action === "status_changed") return `Status changed from ${String(details.from ?? "unknown")} to ${String(details.to ?? "unknown")}`;
  if (activity.action === "created") return "Task created";
  if (activity.action === "subtask_added") return `Subtask added: ${String(details.title ?? "")}`;
  if (activity.action === "subtask_deleted") return `Subtask removed: ${String(details.title ?? "")}`;
  if (activity.action === "subtask_updated") return "Subtask updated";
  const fields = Array.isArray(details.fields) ? details.fields.map(String).join(", ") : "task details";
  return `Updated ${fields}`;
}

export function TaskDetailDrawer({ task, onClose, onSaved }: { task: Task; onClose: () => void; onSaved: (task: Task) => void }) {
  const [title, setTitle] = React.useState(task.title);
  const [description, setDescription] = React.useState(task.description ?? "");
  const [notes, setNotes] = React.useState(task.notes ?? "");
  const [priority, setPriority] = React.useState(task.priority);
  const [deadline, setDeadline] = React.useState(toDateInput(task.deadline));
  const [estimate, setEstimate] = React.useState(task.estimated_minutes?.toString() ?? "");
  const [subtasks, setSubtasks] = React.useState<TaskSubtask[]>([]);
  const [activities, setActivities] = React.useState<TaskActivity[]>([]);
  const [subtaskTitle, setSubtaskTitle] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadDetails = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [subtaskItems, activityItems] = await Promise.all([getTaskSubtasks(task.id), getTaskActivity(task.id)]);
      setSubtasks(subtaskItems);
      setActivities(activityItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load task details. Retry to try again.");
    } finally {
      setLoading(false);
    }
  }, [task.id]);

  React.useEffect(() => {
    const timer = window.setTimeout(() => { void loadDetails(); }, 0);
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = oldOverflow;
      window.clearTimeout(timer);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [loadDetails, onClose]);

  async function saveDetails(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    const changes: UpdateTaskInput = {
      title: title.trim(),
      description: description.trim() || null,
      notes: notes.trim() || null,
      priority,
      estimated_minutes: estimate ? Number(estimate) : null,
      deadline: deadline ? new Date(`${deadline}T12:00:00`).toISOString() : null,
    };
    try {
      const updated = await updateTask(task.id, changes);
      onSaved(updated);
      setActivities(await getTaskActivity(task.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save task details.");
    } finally {
      setSaving(false);
    }
  }

  async function addSubtask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = subtaskTitle.trim();
    if (!value) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createTaskSubtask(task.id, value);
      setSubtasks((current) => [...current, created]);
      setSubtaskTitle("");
      setActivities(await getTaskActivity(task.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add subtask.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleSubtask(subtask: TaskSubtask) {
    setError(null);
    const snapshot = subtasks;
    setSubtasks((current) => current.map((item) => item.id === subtask.id ? { ...item, is_completed: !item.is_completed } : item));
    try {
      await updateTaskSubtask(task.id, subtask.id, { is_completed: !subtask.is_completed });
      setActivities(await getTaskActivity(task.id));
    } catch (err) {
      setSubtasks(snapshot);
      setError(err instanceof Error ? err.message : "Unable to update subtask.");
    }
  }

  async function removeSubtask(subtask: TaskSubtask) {
    const snapshot = subtasks;
    setSubtasks((current) => current.filter((item) => item.id !== subtask.id));
    try {
      await deleteTaskSubtask(task.id, subtask.id);
      setActivities(await getTaskActivity(task.id));
    } catch (err) {
      setSubtasks(snapshot);
      setError(err instanceof Error ? err.message : "Unable to remove subtask.");
    }
  }

  const focusable = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2";
  return (
    <div className="fixed inset-0 z-[70] flex justify-end bg-slate-950/40" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="task-detail-title" onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const elements = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'));
        const first = elements[0];
        const last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }} className="flex h-full w-full max-w-2xl flex-col overflow-hidden bg-white shadow-2xl dark:bg-slate-900">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 p-5 sm:p-6">
          <div className="min-w-0"><p className="text-xs font-semibold tracking-[0.16em] text-blue-600 uppercase">Task details</p><h2 id="task-detail-title" className="mt-1 break-words text-xl font-bold text-slate-900">{task.title}</h2></div>
          <button autoFocus type="button" onClick={onClose} aria-label="Close task details" className={`rounded-lg p-2 text-slate-500 hover:bg-slate-100 ${focusable}`}><X aria-hidden="true" className="size-5" /></button>
        </header>
        <div className="min-h-0 flex-1 space-y-7 overflow-y-auto p-5 sm:p-6">
          {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><span>{error}</span><button type="button" onClick={() => void loadDetails()} className={`font-semibold underline ${focusable}`}>Retry details</button></div>}
          <form onSubmit={(event) => void saveDetails(event)} className="space-y-4">
            <div><label htmlFor="detail-title" className="mb-1.5 block text-sm font-medium text-slate-700">Title</label><input id="detail-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} required className={`w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /></div>
            <div><label htmlFor="detail-description" className="mb-1.5 block text-sm font-medium text-slate-700">Description</label><textarea id="detail-description" rows={2} value={description} onChange={(event) => setDescription(event.target.value)} className={`w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /></div>
            <div><label htmlFor="detail-notes" className="mb-1.5 block text-sm font-medium text-slate-700">Notes</label><textarea id="detail-notes" rows={4} maxLength={10000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add notes for this task" className={`w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /><p className="mt-1 text-right text-xs text-slate-500">{notes.length}/10000</p></div>
            <div className="grid gap-3 sm:grid-cols-3"><div><label htmlFor="detail-priority" className="mb-1.5 block text-sm font-medium text-slate-700">Priority</label><select id="detail-priority" value={priority} onChange={(event) => setPriority(event.target.value)} className={`w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm ${focusable}`}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div><div><label htmlFor="detail-deadline" className="mb-1.5 block text-sm font-medium text-slate-700">Due date</label><input id="detail-deadline" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} className={`w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /></div><div><label htmlFor="detail-estimate" className="mb-1.5 block text-sm font-medium text-slate-700">Estimate (min)</label><input id="detail-estimate" type="number" min={1} value={estimate} onChange={(event) => setEstimate(event.target.value)} className={`w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /></div></div>
            <button type="submit" disabled={saving} className={`inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 ${focusable}`}>{saving ? "Saving…" : "Save task details"}</button>
          </form>

          <section aria-labelledby="subtasks-heading"><div className="flex items-center justify-between gap-3"><div><h3 id="subtasks-heading" className="text-base font-bold text-slate-900">Subtasks</h3><p className="mt-0.5 text-xs text-slate-500">{subtasks.filter((item) => item.is_completed).length} of {subtasks.length} complete</p></div><Check aria-hidden="true" className="size-5 text-blue-600" /></div>
            {loading ? <div role="status" aria-label="Loading subtasks" className="mt-3 h-20 animate-pulse rounded-xl bg-slate-100" /> : subtasks.length ? <ul className="mt-3 space-y-2">{subtasks.map((subtask) => <li key={subtask.id} className="flex items-center gap-2 rounded-xl border border-slate-200 p-2.5"><button type="button" onClick={() => void toggleSubtask(subtask)} aria-label={`${subtask.is_completed ? "Reopen" : "Complete"} subtask ${subtask.title}`} className={`flex size-8 shrink-0 items-center justify-center rounded-lg text-blue-600 hover:bg-blue-50 ${focusable}`}>{subtask.is_completed ? <Check aria-hidden="true" className="size-4" /> : <Circle aria-hidden="true" className="size-4" />}</button><span className={`min-w-0 flex-1 break-words text-sm ${subtask.is_completed ? "text-slate-400 line-through" : "text-slate-800"}`}>{subtask.title}</span><button type="button" onClick={() => void removeSubtask(subtask)} aria-label={`Delete subtask ${subtask.title}`} className={`rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700 ${focusable}`}><Trash2 aria-hidden="true" className="size-4" /></button></li>)}</ul> : <p className="mt-3 rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">No subtasks yet. Break this task into smaller steps.</p>}
            <form onSubmit={(event) => void addSubtask(event)} className="mt-3 flex gap-2"><label htmlFor="new-subtask" className="sr-only">New subtask title</label><input id="new-subtask" value={subtaskTitle} onChange={(event) => setSubtaskTitle(event.target.value)} maxLength={255} placeholder="Add a subtask" className={`min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2.5 text-sm ${focusable}`} /><button type="submit" disabled={!subtaskTitle.trim() || saving} aria-label="Add subtask" className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white hover:bg-slate-700 disabled:opacity-50 ${focusable}`}><Plus aria-hidden="true" className="size-4" /></button></form>
          </section>

          <section aria-labelledby="task-activity-heading"><div className="flex items-center gap-2"><Clock3 aria-hidden="true" className="size-4 text-slate-500" /><h3 id="task-activity-heading" className="text-base font-bold text-slate-900">Activity</h3></div>
            {loading ? <div role="status" aria-label="Loading activity" className="mt-3 h-20 animate-pulse rounded-xl bg-slate-100" /> : activities.length ? <ol className="mt-3 space-y-3 border-l border-slate-200 pl-4">{activities.map((activity) => <li key={activity.id} className="relative"><span aria-hidden="true" className="absolute -left-[1.3rem] top-1.5 size-2 rounded-full bg-blue-500" /><p className="text-sm text-slate-700">{activitySummary(activity)}</p><time dateTime={activity.created_at} className="mt-0.5 block text-xs text-slate-500">{new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(activity.created_at))}</time></li>)}</ol> : <p className="mt-3 rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">Task changes will appear here.</p>}
          </section>
        </div>
      </section>
    </div>
  );
}
