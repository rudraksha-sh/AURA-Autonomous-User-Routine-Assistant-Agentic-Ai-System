import Link from "next/link";
import { ArrowRight, Flame, TrendingUp } from "lucide-react";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

const DAY_MS = 24 * 60 * 60 * 1000;

function localDayKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function completionDays(tasks: Task[]) {
  const counts = new Map<string, number>();
  for (const task of tasks) {
    if (task.status.toLowerCase() !== "completed") continue;
    const updated = new Date(task.updated_at);
    if (Number.isNaN(updated.getTime())) continue;
    const key = localDayKey(updated);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

function getStreak(days: Map<string, number>, today: Date) {
  const cursor = new Date(today);
  cursor.setHours(0, 0, 0, 0);
  if (!days.has(localDayKey(cursor))) cursor.setDate(cursor.getDate() - 1);
  let streak = 0;
  while (days.has(localDayKey(cursor))) {
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

function progressPercent(tasks: Task[]) {
  if (!tasks.length) return 0;
  return Math.round((tasks.filter((task) => task.status.toLowerCase() === "completed").length / tasks.length) * 100);
}

function GoalRing({ goal, tasks }: { goal: Goal; tasks: Task[] }) {
  const progress = progressPercent(tasks);
  const circumference = 2 * Math.PI * 19;
  return (
    <Link href={`/goals/${goal.id}`} className="flex min-w-0 items-center gap-3 rounded-xl border border-slate-200 p-3 transition hover:border-blue-200 hover:bg-blue-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
      <span className="relative size-12 shrink-0" role="img" aria-label={`${goal.title}: ${progress}% of tasks complete`}>
        <svg viewBox="0 0 44 44" className="size-12 -rotate-90" aria-hidden="true">
          <circle cx="22" cy="22" r="19" fill="none" stroke="currentColor" strokeWidth="4" className="text-slate-200" />
          <circle cx="22" cy="22" r="19" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeDasharray={`${circumference * progress / 100} ${circumference}`} className="text-blue-600" />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-slate-700">{progress}%</span>
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-slate-900">{goal.title}</span>
        <span className="mt-0.5 block text-xs text-slate-500">{tasks.filter((task) => task.status.toLowerCase() === "completed").length} of {tasks.length} tasks complete</span>
      </span>
      <ArrowRight aria-hidden="true" className="size-4 shrink-0 text-slate-400" />
    </Link>
  );
}

function ActivityHeatmap({ days }: { days: Map<string, number> }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const currentSunday = new Date(today);
  currentSunday.setDate(today.getDate() - today.getDay());
  const firstSunday = new Date(currentSunday);
  firstSunday.setDate(currentSunday.getDate() - 77);
  const dates = Array.from({ length: 84 }, (_, index) => new Date(firstSunday.getTime() + index * DAY_MS));
  const labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const maxCount = Math.max(1, ...dates.map((date) => days.get(localDayKey(date)) ?? 0));
  const intensity = (count: number) => count === 0 ? "bg-slate-100" : count / maxCount >= 0.75 ? "bg-blue-700" : count / maxCount >= 0.45 ? "bg-blue-500" : count / maxCount >= 0.2 ? "bg-blue-300" : "bg-blue-100";
  return (
    <div className="mt-4 overflow-x-auto pb-1">
      <div className="grid min-w-[560px] grid-cols-[2rem_1fr] gap-1.5" role="img" aria-label="Task completion activity over the last 12 weeks. Darker squares show more completions.">
        <div className="grid grid-rows-7 gap-1.5">{labels.map((label, row) => <span key={label} className="flex h-3 items-center text-[10px] text-slate-500">{row % 2 === 0 ? label : ""}</span>)}</div>
        <div className="grid grid-flow-col grid-cols-12 grid-rows-7 gap-1.5">
        {dates.map((date) => {
          if (date > today) return <span key={localDayKey(date)} title={`${localDayKey(date)}: no activity yet`} className="size-3 rounded-[3px] bg-transparent" />;
          const count = days.get(localDayKey(date)) ?? 0;
          return <span key={localDayKey(date)} title={`${localDayKey(date)}: ${count} completed`} className={`size-3 rounded-[3px] ${intensity(count)}`} />;
        })}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500"><span>12 weeks ago</span><span>Today</span><span className="flex items-center gap-1.5" aria-hidden="true"><span>Less</span><i className="size-2.5 rounded-sm bg-slate-100"/><i className="size-2.5 rounded-sm bg-blue-100"/><i className="size-2.5 rounded-sm bg-blue-300"/><i className="size-2.5 rounded-sm bg-blue-500"/><i className="size-2.5 rounded-sm bg-blue-700"/><span>More</span></span></div>
    </div>
  );
}

export function CompletionInsights({ goals, tasks, loading, taskError, goalsError, onRetryTasks, onRetryGoals }: { goals: Goal[]; tasks: Task[]; loading: boolean; taskError: string | null; goalsError: string | null; onRetryTasks: () => void; onRetryGoals: () => void }) {
  const days = completionDays(tasks);
  const today = new Date();
  const streak = getStreak(days, today);
  const weekly = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - (6 - index));
    return { date, count: days.get(localDayKey(date)) ?? 0 };
  });
  const maxWeekly = Math.max(1, ...weekly.map((day) => day.count));
  const activeGoals = goals.filter((goal) => goal.status.toLowerCase() === "active");
  const totalWeek = weekly.reduce((sum, day) => sum + day.count, 0);

  return (
    <section className="grid gap-6 xl:grid-cols-2" aria-label="Completion insights">
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-xs font-semibold tracking-[0.16em] text-blue-600 uppercase">Build momentum</p><h2 className="mt-1 text-lg font-bold text-slate-900">Active goal progress</h2><p className="mt-1 text-sm text-slate-500">Completion is based on each goal&apos;s saved tasks.</p></div>
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-600"><Flame aria-hidden="true" className="size-5" /></span>
        </div>
        {loading ? <div className="mt-5 grid gap-3 sm:grid-cols-2" role="status" aria-label="Loading goal progress">{[1, 2].map((item) => <div key={item} className="h-[4.5rem] animate-pulse rounded-xl bg-slate-100" />)}</div> : goalsError ? <div role="alert" className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"><p>{goalsError}</p><button type="button" onClick={onRetryGoals} className="mt-2 font-semibold underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Retry</button></div> : taskError ? <div role="alert" className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"><p>{taskError}</p><button type="button" onClick={onRetryTasks} className="mt-2 font-semibold underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Retry</button></div> : activeGoals.length ? <div className="mt-5 grid gap-3 sm:grid-cols-2">{activeGoals.map((goal) => <GoalRing key={goal.id} goal={goal} tasks={tasks.filter((task) => task.goal_id === goal.id)} />)}</div> : <p className="mt-5 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Create an active goal to see task progress here.</p>}
        <p className="mt-4 flex items-center gap-2 rounded-xl bg-orange-50 px-3 py-2.5 text-sm text-orange-900"><Flame aria-hidden="true" className="size-4 shrink-0" /><span><strong>{streak} day{streak === 1 ? "" : "s"}</strong> current completion streak</span></p>
      </article>

      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-xs font-semibold tracking-[0.16em] text-blue-600 uppercase">Task activity</p><h2 className="mt-1 text-lg font-bold text-slate-900">Your last 7 days</h2><p className="mt-1 text-sm text-slate-500">{totalWeek} task{totalWeek === 1 ? "" : "s"} marked complete this week.</p></div>
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><TrendingUp aria-hidden="true" className="size-5" /></span>
        </div>
        {loading ? <div className="mt-5 h-32 animate-pulse rounded-xl bg-slate-100" role="status" aria-label="Loading weekly activity" /> : taskError ? <div role="alert" className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"><p>{taskError}</p><button type="button" onClick={onRetryTasks} className="mt-2 font-semibold underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Retry</button></div> : <div className="mt-5">
          <div className="flex h-28 items-end gap-2" role="img" aria-label={`Daily task completions for the last seven days: ${weekly.map(({ date, count }) => `${date.toLocaleDateString("en", { weekday: "long" })} ${count}`).join(", ")}`}>
            {weekly.map(({ date, count }) => <div key={localDayKey(date)} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"><span className="text-[10px] font-semibold text-slate-600">{count || ""}</span><span className="w-full max-w-8 rounded-t-md bg-blue-500" style={{ height: `${Math.max(count ? 8 : 2, (count / maxWeekly) * 76)}px` }} /><span className="text-[10px] text-slate-500">{date.toLocaleDateString("en", { weekday: "short" })}</span></div>)}
          </div>
          <h3 className="mt-5 text-sm font-semibold text-slate-800">12-week activity</h3>
          <ActivityHeatmap days={days} />
        </div>}
        <p className="mt-3 text-[11px] leading-4 text-slate-500">Completion dates use the task&apos;s last updated time because a separate completion timestamp is not available yet.</p>
      </article>
    </section>
  );
}
