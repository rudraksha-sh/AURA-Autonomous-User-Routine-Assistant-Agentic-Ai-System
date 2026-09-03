"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";

import type { Goal } from "@/types/goal";

type GoalCardProps = {
  goal: Goal;
  onDelete: (goalId: number) => Promise<void>;
  isDeleting: boolean;
};

export function GoalCard({
  goal,
  onDelete,
  isDeleting,
}: GoalCardProps) {
  async function handleDelete() {
    const confirmed = window.confirm(
      `Delete "${goal.title}"? This action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    await onDelete(goal.id);
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <Link
            href={`/goals/${goal.id}`}
            className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
          >
            <h3 className="truncate font-semibold text-slate-900 hover:text-slate-600">
              {goal.title}
            </h3>

            {goal.description && (
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">
                {goal.description}
              </p>
            )}
          </Link>

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
          onClick={handleDelete}
          disabled={isDeleting}
          aria-label={`Delete ${goal.title}`}
          className="flex size-10 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 className="size-5" />
        </button>
      </div>
    </article>
  );
}