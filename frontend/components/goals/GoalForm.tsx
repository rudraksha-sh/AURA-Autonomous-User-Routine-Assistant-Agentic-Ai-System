"use client";

import * as React from "react";
import { Plus } from "lucide-react";

type GoalFormProps = {
  onSubmit: (data: {
    title: string;
    description: string | null;
    priority: string;
  }) => Promise<void>;
  isSubmitting: boolean;
};

export function GoalForm({
  onSubmit,
  isSubmitting,
}: GoalFormProps) {
  const [title, setTitle] = React.useState("");
  const [titleError, setTitleError] = React.useState<string | null>(null);
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("medium");

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!title.trim()) {
      setTitleError("Enter a goal title.");
      return;
    }

    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
        priority,
      });
    } catch {
      // The parent displays the API error and the entered values stay available to retry.
      return;
    }

    setTitle("");
    setTitleError(null);
    setDescription("");
    setPriority("medium");
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Plus className="size-5 text-slate-700" />
        <h2 className="text-lg font-semibold text-slate-900">
          Create a goal
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
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
            onChange={(event) => {
              setTitle(event.target.value);
              if (event.target.value.trim()) setTitleError(null);
            }}
            placeholder="e.g. Prepare for machine learning exam"
            maxLength={255}
            required
            aria-invalid={titleError ? "true" : "false"}
            aria-describedby={titleError ? "goal-title-error" : undefined}
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
          />
          {titleError && (
            <p id="goal-title-error" role="alert" className="mt-2 text-sm text-rose-600">
              {titleError}
            </p>
          )}
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
          disabled={isSubmitting}
          className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Creating..." : "Create goal"}
        </button>
      </form>
    </section>
  );
}
