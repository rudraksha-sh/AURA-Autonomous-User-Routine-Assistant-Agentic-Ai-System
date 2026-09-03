"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, Save } from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { getGoal, updateGoal } from "@/services/goals";
import type { Goal } from "@/types/goal";

export default function GoalDetailPage() {
  const params = useParams();
  const router = useRouter();

  const goalId = Number(params.id);

  const [goal, setGoal] = React.useState<Goal | null>(null);
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("medium");
  const [status, setStatus] = React.useState("active");
  const [deadline, setDeadline] = React.useState("");

  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);

  React.useEffect(() => {
    let isMounted = true;

    async function loadGoal() {
      if (!Number.isInteger(goalId) || goalId <= 0) {
        setError("Invalid goal.");
        setIsLoading(false);
        return;
      }

      try {
        const data = await getGoal(goalId);

        if (isMounted) {
          setGoal(data);
          setTitle(data.title);
          setDescription(data.description ?? "");
          setPriority(data.priority);
          setStatus(data.status);
          setDeadline(
            data.deadline ? data.deadline.slice(0, 16) : ""
          );
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Unable to load goal."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadGoal();

    return () => {
      isMounted = false;
    };
  }, [goalId]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!goal) {
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      setSuccess(false);

      const updatedGoal = await updateGoal(goal.id, {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        status,
        deadline: deadline
          ? new Date(deadline).toISOString()
          : null,
      });

      setGoal(updatedGoal);
      setSuccess(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to update goal."
      );
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">
          Loading goal...
        </p>
      </div>
    );
  }

  if (error || !goal) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Unable to load goal
          </h2>

          <p className="mt-2 text-sm text-slate-500">
            {error ?? "Goal not found."}
          </p>

          <Link
            href="/goals"
            className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            Back to goals
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header userName="User" />

        <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <Link
            href="/goals"
            className="inline-flex items-center gap-2 rounded-lg text-sm font-medium text-slate-500 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
          >
            <ArrowLeft className="size-4" />
            Back to goals
          </Link>

          <div className="mt-6">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Edit goal
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Update the details AURA uses to manage this goal.
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

          {success && (
            <div
              role="status"
              className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700"
            >
              Goal updated successfully.
            </div>
          )}

          <form
            onSubmit={handleSave}
            className="mt-8 space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
          >
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
                rows={5}
                className="mt-2 w-full resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
              />
            </div>

            <div className="grid gap-6 sm:grid-cols-3">
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
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="goal-status"
                  className="text-sm font-medium text-slate-700"
                >
                  Status
                </label>

                <select
                  id="goal-status"
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                >
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="archived">Archived</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="goal-deadline"
                  className="text-sm font-medium text-slate-700"
                >
                  Deadline
                </label>

                <input
                  id="goal-deadline"
                  type="datetime-local"
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSaving || !title.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Save className="size-4" />
                {isSaving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">
              Goal information
            </h2>

            <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Goal ID</dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {goal.id}
                </dd>
              </div>

              <div>
                <dt className="text-slate-500">Created</dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {new Date(goal.created_at).toLocaleString()}
                </dd>
              </div>

              <div>
                <dt className="text-slate-500">Last updated</dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {new Date(goal.updated_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </section>

          <div className="mt-8">
            <button
              type="button"
              onClick={() => router.push("/goals")}
              className="text-sm font-medium text-slate-500 hover:text-slate-900"
            >
              Return to all goals
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}