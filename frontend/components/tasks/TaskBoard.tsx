"use client";

import * as React from "react";
import { DndContext, KeyboardSensor, PointerSensor, closestCorners, useDroppable, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Check, Circle, GripVertical, Trash2 } from "lucide-react";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

const COLUMNS = [
  { id: "pending", title: "Pending", color: "border-t-slate-400" },
  { id: "in_progress", title: "In Progress", color: "border-t-blue-500" },
  { id: "completed", title: "Completed", color: "border-t-emerald-500" },
] as const;

function dueLabel(task: Task) {
  if (!task.deadline) return "No due date";
  const date = new Date(task.deadline);
  return Number.isNaN(date.getTime()) ? "No due date" : `Due ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date)}`;
}

function SortableTaskCard({ task, goal, selected, reorderingEnabled, onSelect, onToggle, onOpen, onDelete }: { task: Task; goal?: Goal; selected: boolean; reorderingEnabled: boolean; onSelect: (checked: boolean) => void; onToggle: () => void; onOpen: () => void; onDelete: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id, disabled: !reorderingEnabled });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <article ref={setNodeRef} style={style} className={`rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md ${isDragging ? "z-10 opacity-60 shadow-lg" : ""}`}>
      <div className="flex items-start gap-2">
        <input type="checkbox" checked={selected} onChange={(event) => onSelect(event.target.checked)} aria-label={`Select ${task.title}`} className="mt-1 size-4 rounded border-slate-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-600" />
        <button type="button" onClick={onToggle} aria-label={`${task.status === "completed" ? "Reopen" : "Complete"} ${task.title}`} className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg text-blue-600 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">{task.status === "completed" ? <Check aria-hidden="true" className="size-4" /> : <Circle aria-hidden="true" className="size-4" />}</button>
        <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><span className={`block break-words text-sm font-semibold ${task.status === "completed" ? "text-slate-400 line-through" : "text-slate-900"}`}>{task.title}</span><span className="mt-1 block truncate text-xs text-slate-500">{goal?.title ?? "Goal"}</span></button>
        <button type="button" onClick={onDelete} aria-label={`Delete ${task.title}`} className="flex size-8 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><Trash2 aria-hidden="true" className="size-4" /></button>
        <button type="button" {...attributes} {...listeners} aria-label={`Drag ${task.title}. Press space or enter to pick up, arrow keys to move, then space or enter to drop.`} disabled={!reorderingEnabled} className="flex size-8 shrink-0 touch-none items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:cursor-not-allowed disabled:opacity-40"><GripVertical aria-hidden="true" className="size-4" /></button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 pl-9 text-[11px]">
        <span className={`rounded-full px-2 py-1 font-semibold capitalize ${task.priority === "high" ? "bg-rose-50 text-rose-700" : task.priority === "medium" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>{task.priority}</span>
        <span className="text-slate-500">{dueLabel(task)}</span>
        {task.estimated_minutes && <span className="text-slate-500">{task.estimated_minutes} min</span>}
      </div>
    </article>
  );
}

function BoardColumn({ id, title, color, tasks, goals, selectedIds, reorderingEnabled, onSelect, onToggle, onOpen, onDelete }: { id: string; title: string; color: string; tasks: Task[]; goals: Goal[]; selectedIds: Set<number>; reorderingEnabled: boolean; onSelect: (taskId: number, checked: boolean) => void; onToggle: (task: Task) => void; onOpen: (task: Task) => void; onDelete: (task: Task) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <section ref={setNodeRef} aria-labelledby={`column-${id}`} className={`min-h-80 min-w-[17rem] flex-1 rounded-2xl border border-slate-200 border-t-4 ${color} bg-slate-50/70 p-3 transition-colors ${isOver ? "bg-blue-50" : ""}`}>
      <header className="mb-3 flex items-center justify-between gap-3 px-1"><h2 id={`column-${id}`} className="text-sm font-bold text-slate-800">{title}</h2><span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">{tasks.length}</span></header>
      <SortableContext items={tasks.map((task) => task.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2" aria-label={`${title} tasks`}>
          {tasks.map((task) => <SortableTaskCard key={task.id} task={task} goal={goals.find((goal) => goal.id === task.goal_id)} selected={selectedIds.has(task.id)} reorderingEnabled={reorderingEnabled} onSelect={(checked) => onSelect(task.id, checked)} onToggle={() => onToggle(task)} onOpen={() => onOpen(task)} onDelete={() => onDelete(task)} />)}
          {tasks.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-4 text-center text-xs text-slate-500">Drop a task here</p>}
        </div>
      </SortableContext>
    </section>
  );
}

export function TaskBoard({ tasks, goals, selectedIds, reorderingEnabled, onSelect, onToggle, onOpen, onDelete, onReorder }: { tasks: Task[]; goals: Goal[]; selectedIds: Set<number>; reorderingEnabled: boolean; onSelect: (taskId: number, checked: boolean) => void; onToggle: (task: Task) => void; onOpen: (task: Task) => void; onDelete: (task: Task) => void; onReorder: (orders: Array<{ status: string; ids: number[] }>) => void }) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  function finishDrag(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeTask = tasks.find((task) => task.id === Number(active.id));
    if (!activeTask) return;
    const overTask = tasks.find((task) => task.id === Number(over.id));
    const destinationStatus = overTask?.status ?? String(over.id);
    if (!COLUMNS.some((column) => column.id === destinationStatus)) return;
    const origin = tasks.filter((task) => task.status === activeTask.status).sort((a, b) => a.position - b.position || a.id - b.id);
    const destination = activeTask.status === destinationStatus ? origin : tasks.filter((task) => task.status === destinationStatus).sort((a, b) => a.position - b.position || a.id - b.id);
    const fromIndex = origin.findIndex((task) => task.id === activeTask.id);
    const toIndex = overTask ? destination.findIndex((task) => task.id === overTask.id) : destination.length;
    if (fromIndex < 0 || toIndex < 0) return;
    if (activeTask.status === destinationStatus) {
      const reordered = arrayMove(origin, fromIndex, toIndex);
      onReorder([{ status: destinationStatus, ids: reordered.map((task) => task.id) }]);
      return;
    }
    const remaining = origin.filter((task) => task.id !== activeTask.id);
    const moved = { ...activeTask, status: destinationStatus };
    const inserted = [...destination];
    inserted.splice(toIndex, 0, moved);
    onReorder([
      { status: destinationStatus, ids: inserted.map((task) => task.id) },
      { status: activeTask.status, ids: remaining.map((task) => task.id) },
    ]);
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={finishDrag}>
      <div className="flex gap-4 overflow-x-auto pb-3" aria-label="Task board">
        {COLUMNS.map((column) => <BoardColumn key={column.id} {...column} tasks={tasks.filter((task) => task.status === column.id).sort((a, b) => a.position - b.position || a.id - b.id)} goals={goals} selectedIds={selectedIds} reorderingEnabled={reorderingEnabled} onSelect={onSelect} onToggle={onToggle} onOpen={onOpen} onDelete={onDelete} />)}
      </div>
    </DndContext>
  );
}
