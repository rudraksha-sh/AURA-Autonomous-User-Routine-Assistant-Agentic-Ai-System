"use client";

import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { createGoal, deleteGoal, getGoals } from "@/services/goals";
import type { CreateGoalInput, Goal } from "@/types/goal";

export default function GoalsPage() {
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isCreating, setIsCreating] = React.useState(false);

  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("medium");

  React.useEffect(() => {
    let isMounted = true;

    async function loadGoals() {
      try {
        const data = await getGoals();

        if (isMounted) {
          setGoals(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Unable to load goals."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadGoals();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleCreateGoal(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!title.trim()) {
      return;
    }

    try {
      setIsCreating(true);
      setError(null);

      const payload: CreateGoalInput = {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        status: "active",
      };

      const newGoal = await createGoal(payload);

      setGoals((currentGoals) => [newGoal, ...currentGoals]);

      setTitle("");
      setDescription("");
      setPriority("medium");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create goal."
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDeleteGoal(goalId: number) {
    try {
      setError(null);
      await deleteGoal(goalId);

      setGoals((currentGoals) =>
        currentGoals.filter((goal) => goal.id !== goalId)
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to delete goal."
      );
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header userName="User" />

        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Goals
            </h1>

            <p className="mt-2 text-sm text-slate-500 sm:text-base">
              Create and manage the goals AURA will help you accomplish.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <Plus className="size-5 text-slate-700" />

              <h2 className="text-lg font-semibold text-slate-900">
                Create a goal
              </h2>
            </div>

            <form onSubmit={handleCreateGoal} className="mt-5 space-y-4">
              <div>
                <label
                  htmlFor="goal-title"
                  className="text-sm font-medium text-slate-700"
                >
                  Title
                </label>

                <input
                  id="goal-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Prepare for machine learning exam"
                  maxLength={255}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                />
              </div>

              <div>
                <label
                  htmlFor="goal-description"
                  className="text-sm font-medium text-slate-700"
                >
                  Description
                </label>

                <textarea
                  id="goal-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Describe what you want to accomplish..."
                  rows={3}
                  className="mt-2 w-full resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                />
              </div>

              <div>
                <label
                  htmlFor="goal-priority"
                  className="text-sm font-medium text-slate-700"
                >
                  Priority
                </label>

                <select
                  id="goal-priority"
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200 sm:w-48"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isCreating}
                className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isCreating ? "Creating..." : "Create goal"}
              </button>
            </form>
          </section>

          <section className="mt-8">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Your goals
              </h2>

              <span className="text-sm text-slate-500">
                {goals.length} {goals.length === 1 ? "goal" : "goals"}
              </span>
            </div>

            {isLoading ? (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">
                  Loading your goals...
                </p>
              </div>
            ) : goals.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
                <p className="text-sm font-medium text-slate-700">
                  No goals yet.
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Create your first goal above.
                </p>
              </div>
            ) : (
              <div className="mt-4 grid gap-4">
                {goals.map((goal) => (
                  <article
                    key={goal.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="truncate font-semibold text-slate-900">
                          {goal.title}
                        </h3>

                        {goal.description && (
                          <p className="mt-2 text-sm leading-6 text-slate-500">
                            {goal.description}
                          </p>
                        )}

                        <div className="mt-4 flex flex-wrap gap-2">
                          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                            {goal.status}
                          </span>

                          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                            {goal.priority} priority
                          </span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDeleteGoal(goal.id)}
                        aria-label={`Delete ${goal.title}`}
                        className="flex size-10 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                      >
                        <Trash2 className="size-5" />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}