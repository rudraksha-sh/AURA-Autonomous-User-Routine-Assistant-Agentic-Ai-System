"use client";

import * as React from "react";

import { GoalForm } from "@/components/goals/GoalForm";
import { GoalList } from "@/components/goals/GoalList";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import {
  createGoal,
  deleteGoal,
  getGoals,
} from "@/services/goals";
import type { Goal } from "@/types/goal";

export default function GoalsPage() {
  const [goals, setGoals] = React.useState<Goal[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isCreating, setIsCreating] = React.useState(false);
  const [deletingGoalId, setDeletingGoalId] = React.useState<number | null>(
    null
  );
  const [error, setError] = React.useState<string | null>(null);
  const [loadError, setLoadError] = React.useState(false);
  const [reloadKey, setReloadKey] = React.useState(0);

  const loadGoals = React.useCallback(() => {
    setIsLoading(true);
    setError(null);
    setLoadError(false);
    setReloadKey((current) => current + 1);
  }, []);

  React.useEffect(() => {
    let isMounted = true;

    getGoals()
      .then((data) => {
        if (isMounted) setGoals(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setLoadError(true);
          setError(err instanceof Error ? err.message : "Unable to load goals.");
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  async function handleCreateGoal(data: {
    title: string;
    description: string | null;
    priority: string;
  }) {
    try {
      setIsCreating(true);
      setError(null);

      const newGoal = await createGoal({
        ...data,
        status: "active",
      });

      setGoals((currentGoals) => [newGoal, ...currentGoals]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create goal."
      );

      throw err;
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDeleteGoal(goalId: number) {
    try {
      setDeletingGoalId(goalId);
      setError(null);

      await deleteGoal(goalId);

      setGoals((currentGoals) =>
        currentGoals.filter((goal) => goal.id !== goalId)
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to delete goal."
      );
    } finally {
      setDeletingGoalId(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header userName="User" title="Goals" />

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
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <span>{error}</span>
                {loadError && (
                  <button type="button" onClick={loadGoals} disabled={isLoading} className="shrink-0 font-semibold hover:underline disabled:opacity-50">
                    Retry loading goals
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="mt-8">
            <GoalForm
              onSubmit={handleCreateGoal}
              isSubmitting={isCreating}
            />
          </div>

          <section className="mt-8">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Your goals
              </h2>

              <span className="text-sm text-slate-500">
                {goals.length} {goals.length === 1 ? "goal" : "goals"}
              </span>
            </div>

            {!loadError && (
              <GoalList
                goals={goals}
                isLoading={isLoading}
                deletingGoalId={deletingGoalId}
                onDelete={handleDeleteGoal}
              />
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
