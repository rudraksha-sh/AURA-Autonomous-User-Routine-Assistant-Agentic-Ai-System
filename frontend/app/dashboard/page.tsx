
"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Flag,
  ListTodo,
  Plus,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { ApiError, getMe } from "@/services/auth";
import { clearAccessToken } from "@/services/auth-storage";
import { getGoals } from "@/services/goals";
import type { User } from "@/types/auth";
import type { Goal } from "@/types/goal";

function getGreeting() {
  const hour = new Date().getHours();

  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatDate(date: Date) {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatShortDate(value: string | null) {
  if (!value) return "No deadline";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "No deadline";

  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function isOverdue(goal: Goal) {
  if (!goal.deadline || goal.status !== "active") return false;

  const deadline = new Date(goal.deadline);

  if (Number.isNaN(deadline.getTime())) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  deadline.setHours(0, 0, 0, 0);

  return deadline < today;
}

function isDueSoon(goal: Goal) {
  if (!goal.deadline || goal.status !== "active") return false;

  const deadline = new Date(goal.deadline);

  if (Number.isNaN(deadline.getTime())) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  deadline.setHours(0, 0, 0, 0);

  const days = Math.round(
    (deadline.getTime() - today.getTime()) / 86_400_000
  );

  return days >= 0 && days <= 7;
}

function getPriorityClass(priority: string) {
  switch (priority.toLowerCase()) {
    case "high":
      return "bg-rose-50 text-rose-700 ring-rose-200";
    case "medium":
      return "bg-amber-50 text-amber-700 ring-amber-200";
    case "low":
      return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    default:
      return "bg-slate-100 text-slate-600 ring-slate-200";
  }
}

function getStatusClass(status: string) {
  switch (status.toLowerCase()) {
    case "completed":
      return "bg-emerald-50 text-emerald-700";
    case "archived":
      return "bg-slate-100 text-slate-600";
    default:
      return "bg-blue-50 text-blue-700";
  }
}

function getGoalHref(goal: Goal) {
  return `/goals/${goal.id}`;
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  accent,
  trend,
}: {
  title: string;
  value: number | string;
  description: string;
  icon: typeof Target;
  accent: string;
  trend?: "up" | "down";
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {value}
          </p>
        </div>

        <span
          className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${accent}`}
        >
          <Icon aria-hidden="true" className="size-5" />
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
        {trend === "up" ? (
          <ArrowUpRight aria-hidden="true" className="size-4 text-emerald-600" />
        ) : trend === "down" ? (
          <ArrowDownRight aria-hidden="true" className="size-4 text-amber-600" />
        ) : null}
        <span>{description}</span>
      </div>
    </article>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold tracking-[0.16em] text-blue-600 uppercase">
            {eyebrow}
          </p>
        )}
        <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-sm leading-6 text-slate-500">
            {description}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: typeof Target;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-8 text-center">
      <span className="flex size-12 items-center justify-center rounded-2xl bg-white text-blue-600 shadow-sm ring-1 ring-slate-200">
        <Icon aria-hidden="true" className="size-6" />
      </span>
      <h3 className="mt-4 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm leading-6 text-slate-500">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading dashboard" role="status">
      <span className="sr-only">Loading dashboard...</span>
      <div className="h-36 animate-pulse rounded-2xl bg-slate-200" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-2xl bg-slate-200"
          />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="h-80 animate-pulse rounded-2xl bg-slate-200 xl:col-span-2" />
        <div className="h-80 animate-pulse rounded-2xl bg-slate-200" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = React.useState<User | null>(null);
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [goalsLoading, setGoalsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [goalsError, setGoalsError] = React.useState<string | null>(null);

  const loadGoals = React.useCallback(async () => {
    setGoalsLoading(true);
    setGoalsError(null);

    try {
      const result = await getGoals();
      setGoals(result);
    } catch (err) {
      setGoalsError(
        err instanceof Error ? err.message : "Unable to load your goals."
      );
    } finally {
      setGoalsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      try {
        const currentUser = await getMe();

        if (!isMounted) return;

        setUser(currentUser);

        try {
          const result = await getGoals();

          if (isMounted) {
            setGoals(result);
            setGoalsError(null);
          }
        } catch (err) {
          if (isMounted) {
            setGoalsError(
              err instanceof Error ? err.message : "Unable to load your goals."
            );
          }
        } finally {
          if (isMounted) setGoalsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          if (err instanceof ApiError && err.status === 401) {
            clearAccessToken();
            router.replace("/login");
            return;
          }

          setError(
            err instanceof Error
              ? err.message
              : "Unable to load your account."
          );
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, [router]);

  const activeGoals = goals.filter(
    (goal) => goal.status.toLowerCase() === "active"
  );
  const completedGoals = goals.filter(
    (goal) => goal.status.toLowerCase() === "completed"
  );
  const overdueGoals = activeGoals.filter(isOverdue);
  const dueSoonGoals = activeGoals.filter(isDueSoon);
  const highPriorityGoals = activeGoals.filter(
    (goal) => goal.priority.toLowerCase() === "high"
  );

  const completionRate =
    goals.length > 0
      ? Math.round((completedGoals.length / goals.length) * 100)
      : 0;

  const upcomingGoals = [...activeGoals]
    .filter((goal) => goal.deadline && !isOverdue(goal))
    .sort(
      (a, b) =>
        new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime()
    )
    .slice(0, 4);

  const recentGoals = [...goals]
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() -
        new Date(a.updated_at).getTime()
    )
    .slice(0, 4);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 md:flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Header userName="Loading..." />
          <main className="mx-auto w-full max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
            <DashboardSkeleton />
          </main>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="min-h-screen bg-slate-50 md:flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Header userName="Guest" />
          <main className="mx-auto flex min-h-[70vh] max-w-2xl items-center justify-center px-4 py-12">
            <section
              role="alert"
              className="w-full rounded-2xl border border-rose-200 bg-white p-6 text-center shadow-sm sm:p-10"
            >
              <span className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
                <CircleAlert aria-hidden="true" className="size-7" />
              </span>
              <h2 className="mt-4 text-xl font-bold text-slate-900">
                Unable to load your dashboard
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {error ?? "Authentication required."}
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
              >
                <RefreshCw aria-hidden="true" className="size-4" />
                Try again
              </button>
            </section>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header userName={user.name} />

        <main className="mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          {/* Welcome */}
          <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-lg shadow-blue-900/10 sm:p-8 lg:p-10">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -right-12 -top-20 size-64 rounded-full border border-white/10"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -right-4 -top-12 size-48 rounded-full border border-white/10"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -bottom-28 right-32 size-64 rounded-full bg-white/5 blur-2xl"
            />

            <div className="relative flex flex-col justify-between gap-7 sm:flex-row sm:items-end">
              <div className="max-w-2xl">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-blue-50">
                  <Sparkles aria-hidden="true" className="size-3.5" />
                  Your personal routine workspace
                </span>

                <h2 className="mt-5 text-2xl font-bold tracking-tight sm:text-3xl lg:text-4xl">
                  {getGreeting()}, {user.name.split(" ")[0]}!
                </h2>

                <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">
                  Small, consistent steps create meaningful progress.
                  Here&apos;s your current overview.
                </p>

                <p className="mt-4 flex items-center gap-2 text-sm text-blue-100">
                  <CalendarDays aria-hidden="true" className="size-4" />
                  {formatDate(new Date())}
                </p>
              </div>

              <Link
                href="/goals"
                className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-xl bg-white px-4 py-3 text-sm font-semibold text-blue-700 shadow-sm transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600 sm:self-auto"
              >
                <Plus aria-hidden="true" className="size-4" />
                Create a goal
              </Link>
            </div>
          </section>

          {/* Summary metrics */}
          <section aria-label="Goal summary">
            <SectionHeading
              eyebrow="Your overview"
              title="Progress at a glance"
              description="A live summary calculated from your saved goals."
            />

            <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                title="Total goals"
                value={goalsLoading ? "..." : goals.length}
                description="All saved goals"
                icon={Target}
                accent="bg-blue-50 text-blue-600"
              />

              <MetricCard
                title="Active goals"
                value={goalsLoading ? "..." : activeGoals.length}
                description="Goals in progress"
                icon={TrendingUp}
                accent="bg-indigo-50 text-indigo-600"
                trend="up"
              />

              <MetricCard
                title="Completed goals"
                value={goalsLoading ? "..." : completedGoals.length}
                description="Goals marked completed"
                icon={CheckCircle2}
                accent="bg-emerald-50 text-emerald-600"
                trend="up"
              />

              <MetricCard
                title="Overdue goals"
                value={goalsLoading ? "..." : overdueGoals.length}
                description="Active goals past their deadline"
                icon={Clock3}
                accent="bg-amber-50 text-amber-600"
                trend={overdueGoals.length > 0 ? "down" : undefined}
              />
            </div>
          </section>

          {goalsError && (
            <div
              role="alert"
              className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 sm:flex-row sm:items-center sm:justify-between"
            >
              <span>{goalsError}</span>
              <button
                type="button"
                onClick={loadGoals}
                disabled={goalsLoading}
                className="inline-flex shrink-0 items-center gap-2 self-start font-semibold hover:underline disabled:opacity-50 sm:self-center"
              >
                <RefreshCw
                  aria-hidden="true"
                  className={`size-4 ${goalsLoading ? "animate-spin" : ""}`}
                />
                Retry
              </button>
            </div>
          )}

          {/* Main dashboard columns */}
          <div className="grid items-start gap-6 xl:grid-cols-3">
            <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-2">
              <SectionHeading
                eyebrow="Stay on track"
                title="Your goals"
                description="Keep your priorities visible and your next steps clear."
                action={
                  <Link
                    href="/goals"
                    className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700"
                  >
                    View all
                    <ArrowRight aria-hidden="true" className="size-4" />
                  </Link>
                }
              />

              <div className="mt-6">
                {goalsLoading ? (
                  <div className="space-y-3" role="status">
                    <span className="sr-only">Loading goals...</span>
                    {[1, 2, 3].map((item) => (
                      <div
                        key={item}
                        className="h-24 animate-pulse rounded-xl bg-slate-100"
                      />
                    ))}
                  </div>
                ) : goalsError ? (
                  <EmptyState
                    icon={CircleAlert}
                    title="Goals couldn't be loaded"
                    description="Retry loading your goals to see your latest progress."
                    action={
                      <button
                        type="button"
                        onClick={loadGoals}
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                      >
                        <RefreshCw aria-hidden="true" className="size-4" />
                        Retry
                      </button>
                    }
                  />
                ) : goals.length === 0 ? (
                  <EmptyState
                    icon={Target}
                    title="Start with your first goal"
                    description="Add a goal you care about. It will appear here so you can keep track of it."
                    action={
                      <Link
                        href="/goals"
                        className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
                      >
                        <Plus aria-hidden="true" className="size-4" />
                        Create your first goal
                      </Link>
                    }
                  />
                ) : (
                  <div className="space-y-3">
                    {recentGoals.map((goal) => (
                      <Link
                        key={goal.id}
                        href={getGoalHref(goal)}
                        className="group flex min-w-0 items-start gap-3 rounded-xl border border-slate-200 p-4 transition hover:border-blue-200 hover:bg-blue-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                      >
                        <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                          {goal.status.toLowerCase() === "completed" ? (
                            <CheckCircle2
                              aria-hidden="true"
                              className="size-5"
                            />
                          ) : (
                            <Flag aria-hidden="true" className="size-5" />
                          )}
                        </span>

                        <span className="min-w-0 flex-1">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="break-words text-sm font-semibold text-slate-900 group-hover:text-blue-700">
                              {goal.title}
                            </span>
                            <span
                              className={`rounded-full px-2 py-1 text-[11px] font-semibold capitalize ${getStatusClass(goal.status)}`}
                            >
                              {goal.status}
                            </span>
                          </span>

                          <span className="mt-1 block text-sm leading-5 text-slate-500">
                            {goal.description || "No description added yet."}
                          </span>

                          <span className="mt-3 flex flex-wrap items-center gap-2">
                            <span
                              className={`rounded-full px-2 py-1 text-[11px] font-semibold capitalize ring-1 ring-inset ${getPriorityClass(goal.priority)}`}
                            >
                              {goal.priority} priority
                            </span>
                            {goal.deadline && (
                              <span
                                className={`inline-flex items-center gap-1 text-xs ${isOverdue(goal) ? "font-semibold text-rose-600" : "text-slate-500"}`}
                              >
                                <CalendarDays
                                  aria-hidden="true"
                                  className="size-3.5"
                                />
                                {isOverdue(goal) ? "Overdue · " : ""}
                                {formatShortDate(goal.deadline)}
                              </span>
                            )}
                          </span>
                        </span>

                        <ArrowRight
                          aria-hidden="true"
                          className="mt-1 size-4 shrink-0 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-blue-600"
                        />
                      </Link>
                    ))}

                    {goals.length > recentGoals.length && (
                      <Link
                        href="/goals"
                        className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                      >
                        See all {goals.length} goals
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* Progress panel */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <SectionHeading
                eyebrow="Keep moving"
                title="Goal completion"
                description="How many of your saved goals are complete."
              />

              {goalsLoading ? (
                <div className="mt-6 h-44 animate-pulse rounded-xl bg-slate-100" />
              ) : goalsError ? (
                <p className="mt-6 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  Progress is unavailable until your goals load successfully.
                </p>
              ) : (
                <>
                  <div className="mt-7 flex items-center gap-5">
                    <div
                      className="relative flex size-28 shrink-0 items-center justify-center rounded-full"
                      style={{
                        background: `conic-gradient(#2563eb ${completionRate}%, #e2e8f0 ${completionRate}% 100%)`,
                      }}
                      role="img"
                      aria-label={`${completionRate}% of goals completed`}
                    >
                      <div className="flex size-20 flex-col items-center justify-center rounded-full bg-white">
                        <span className="text-2xl font-bold text-slate-900">
                          {completionRate}%
                        </span>
                        <span className="text-[10px] font-medium text-slate-500">
                          complete
                        </span>
                      </div>
                    </div>

                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900">
                        {goals.length === 0
                          ? "Your journey starts here"
                          : completionRate === 100
                            ? "All goals completed!"
                            : "Keep up the momentum"}
                      </p>
                      <p className="mt-1 text-sm leading-5 text-slate-500">
                        {completedGoals.length} of {goals.length} goals
                        completed.
                      </p>
                    </div>
                  </div>

                  <div className="mt-7 space-y-4">
                    <div>
                      <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="text-slate-600">Active</span>
                        <span className="font-semibold text-slate-900">
                          {activeGoals.length}
                        </span>
                      </div>
                      <div
                        className="h-2 overflow-hidden rounded-full bg-slate-100"
                        role="progressbar"
                        aria-label="Active goals share"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={
                          goals.length
                            ? Math.round((activeGoals.length / goals.length) * 100)
                            : 0
                        }
                      >
                        <div
                          className="h-full rounded-full bg-blue-500 transition-all"
                          style={{
                            width: `${goals.length ? (activeGoals.length / goals.length) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="text-slate-600">Completed</span>
                        <span className="font-semibold text-slate-900">
                          {completedGoals.length}
                        </span>
                      </div>
                      <div
                        className="h-2 overflow-hidden rounded-full bg-slate-100"
                        role="progressbar"
                        aria-label="Completed goals share"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={completionRate}
                      >
                        <div
                          className="h-full rounded-full bg-emerald-500 transition-all"
                          style={{ width: `${completionRate}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}

              <Link
                href="/goals"
                className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
              >
                Manage goals
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </section>
          </div>

          {/* Schedule and attention */}
          <div className="grid items-start gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <SectionHeading
                eyebrow="Plan ahead"
                title="Upcoming deadlines"
                description="Active goals with the nearest deadlines."
                action={
                  <span className="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <CalendarDays aria-hidden="true" className="size-5" />
                  </span>
                }
              />

              <div className="mt-5">
                {goalsLoading ? (
                  <div className="h-36 animate-pulse rounded-xl bg-slate-100" />
                ) : goalsError ? (
                  <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
                    Deadlines are unavailable because goals could not be loaded.
                  </p>
                ) : upcomingGoals.length === 0 ? (
                  <EmptyState
                    icon={CalendarDays}
                    title="No upcoming deadlines"
                    description={
                      activeGoals.length === 0
                        ? "Create an active goal to start planning your next steps."
                        : "Your active goals have no upcoming deadlines. You can add one when editing a goal."
                    }
                    action={
                      <Link
                        href="/goals"
                        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                      >
                        View goals <span aria-hidden="true">→</span>
                      </Link>
                    }
                  />
                ) : (
                  <div className="space-y-1">
                    {upcomingGoals.map((goal) => (
                      <Link
                        key={goal.id}
                        href={getGoalHref(goal)}
                        className="flex items-center gap-3 rounded-xl px-3 py-3 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                      >
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                          <Clock3 aria-hidden="true" className="size-5" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-slate-900">
                            {goal.title}
                          </span>
                          <span className="mt-1 block text-xs text-slate-500">
                            Due {formatShortDate(goal.deadline)}
                          </span>
                        </span>
                        <span
                          className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-semibold capitalize ring-1 ring-inset ${getPriorityClass(goal.priority)}`}
                        >
                          {goal.priority}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <SectionHeading
                eyebrow="Stay organized"
                title="Today's routine"
                description="Your daily tasks will live here."
                action={
                  <span className="flex size-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                    <ListTodo aria-hidden="true" className="size-5" />
                  </span>
                }
              />

              <div className="mt-5">
                <EmptyState
                  icon={ListTodo}
                  title="Your routine planner is ready"
                  description="A routine or task service is not connected to this dashboard yet. Your goal data is available above; daily task counts are not fabricated."
                  action={
                    <Link
                      href="/goals"
                      className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
                    >
                      <Plus aria-hidden="true" className="size-4" />
                      Plan with a goal
                    </Link>
                  }
                />
              </div>
            </section>
          </div>

          {/* Attention and quick actions */}
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 lg:col-span-2">
              <SectionHeading
                eyebrow="Your next steps"
                title="Focus for today"
                description="A short, actionable overview based on your current goals."
              />

              {goalsLoading ? (
                <div className="mt-5 h-28 animate-pulse rounded-xl bg-slate-100" />
              ) : goalsError ? (
                <p className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
                  Your focus suggestions will appear when your goals load.
                </p>
              ) : goals.length === 0 ? (
                <div className="mt-5 rounded-xl bg-blue-50/70 p-5">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Choose one meaningful goal
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Start small. Add a goal and give yourself a clear next step.
                  </p>
                  <Link
                    href="/goals"
                    className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-800"
                  >
                    Create a goal
                    <ArrowRight aria-hidden="true" className="size-4" />
                  </Link>
                </div>
              ) : (
                <div className="mt-5 space-y-3">
                  {overdueGoals.length > 0 && (
                    <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4">
                      <CircleAlert
                        aria-hidden="true"
                        className="mt-0.5 size-5 shrink-0 text-rose-600"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-rose-900">
                          Review overdue goals
                        </p>
                        <p className="mt-1 text-sm leading-5 text-rose-700">
                          {overdueGoals.length} active{" "}
                          {overdueGoals.length === 1 ? "goal is" : "goals are"}{" "}
                          past the deadline.
                        </p>
                        <Link
                          href="/goals"
                          className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-rose-700 hover:underline"
                        >
                          Review goals
                          <ArrowRight aria-hidden="true" className="size-4" />
                        </Link>
                      </div>
                    </div>
                  )}

                  {dueSoonGoals.length > 0 && (
                    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
                      <Clock3
                        aria-hidden="true"
                        className="mt-0.5 size-5 shrink-0 text-amber-600"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-amber-900">
                          Deadlines approaching
                        </p>
                        <p className="mt-1 text-sm leading-5 text-amber-800">
                          {dueSoonGoals.length} active{" "}
                          {dueSoonGoals.length === 1 ? "goal is" : "goals are"}{" "}
                          due within the next seven days.
                        </p>
                      </div>
                    </div>
                  )}

                  {highPriorityGoals.length > 0 && (
                    <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50/70 p-4">
                      <Target
                        aria-hidden="true"
                        className="mt-0.5 size-5 shrink-0 text-blue-600"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-blue-900">
                          Keep high-priority goals in view
                        </p>
                        <p className="mt-1 text-sm leading-5 text-blue-800">
                          You have {highPriorityGoals.length} active high-priority{" "}
                          {highPriorityGoals.length === 1 ? "goal" : "goals"}.
                        </p>
                      </div>
                    </div>
                  )}

                  {overdueGoals.length === 0 &&
                    dueSoonGoals.length === 0 &&
                    highPriorityGoals.length === 0 && (
                      <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                        <CheckCircle2
                          aria-hidden="true"
                          className="mt-0.5 size-5 shrink-0 text-emerald-600"
                        />
                        <div>
                          <p className="text-sm font-semibold text-emerald-900">
                            You&apos;re in a good position
                          </p>
                          <p className="mt-1 text-sm leading-5 text-emerald-800">
                            No overdue or near-deadline goals need attention
                            based on your saved goal data.
                          </p>
                        </div>
                      </div>
                    )}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <SectionHeading
                eyebrow="Quick access"
                title="Shortcuts"
                description="Get to your next action faster."
              />

              <div className="mt-5 space-y-3">
                <Link
                  href="/goals"
                  className="group flex items-center gap-3 rounded-xl border border-slate-200 p-3 transition hover:border-blue-200 hover:bg-blue-50/50"
                >
                  <span className="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <Plus aria-hidden="true" className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-slate-900">
                      Manage goals
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      Add or review goals
                    </span>
                  </span>
                  <ArrowRight
                    aria-hidden="true"
                    className="size-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-blue-600"
                  />
                </Link>

                <Link
                  href="/goals"
                  className="group flex items-center gap-3 rounded-xl border border-slate-200 p-3 transition hover:border-blue-200 hover:bg-blue-50/50"
                >
                  <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                    <TrendingUp aria-hidden="true" className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-slate-900">
                      Review progress
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      Check goal status
                    </span>
                  </span>
                  <ArrowRight
                    aria-hidden="true"
                    className="size-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-blue-600"
                  />
                </Link>

                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-slate-700">
                    <Sparkles
                      aria-hidden="true"
                      className="size-4 text-blue-600"
                    />
                    <p className="text-sm font-semibold">AURA tip</p>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Give each goal a clear title, a realistic deadline, and a
                    priority to make your overview more useful.
                  </p>
                </div>
              </div>
            </section>
          </div>

          {/* Footer summary */}
          {!goalsLoading && !goalsError && goals.length > 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm sm:flex sm:items-center sm:justify-between sm:gap-4">
              <div className="flex items-center gap-3">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                  <CheckCircle2 aria-hidden="true" className="size-5" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Keep your momentum going
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {completedGoals.length} completed · {activeGoals.length}{" "}
                    active · {goals.length - completedGoals.length - activeGoals.length}{" "}
                    archived or other
                  </p>
                </div>
              </div>
              <Link
                href="/goals"
                className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 sm:mt-0"
              >
                Open goal manager
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </section>
          )}

          <footer className="pb-2 text-center text-xs text-slate-400">
            AURA · Your routine, one step at a time.
          </footer>
        </main>
      </div>
    </div>
  );
}
