"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { createAutonomyGrant, stopAutonomy, transitionAutonomyGrant } from "@/services/planner";
import type { Goal } from "@/types/goal";
import type { AutonomyGrant } from "@/types/workflow";

type Props = {
  goals: Goal[];
  grants: AutonomyGrant[];
  selectedGrant: string;
  onSelect: (value: string) => void;
  onChange: (grant?: AutonomyGrant) => void;
  disabled: boolean;
};

export function AutonomyControls({ goals, grants, selectedGrant, onSelect, onChange, disabled }: Props) {
  const [enabling, setEnabling] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function update(request: () => Promise<AutonomyGrant | undefined>) {
    setPending(true);
    setError("");
    try {
      onChange(await request());
      setEnabling(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update autonomous mode.");
    } finally {
      setPending(false);
    }
  }

  function enable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    void update(() => createAutonomyGrant({
      goal_id: Number(form.get("goal")),
      duration_minutes: Number(form.get("duration")),
      run_limit: Number(form.get("runs")),
      task_limit: Number(form.get("tasks")),
      operation: "goal.tasks.create",
      consent: form.get("consent") === "on",
      consent_version: "local-task-grant-v1",
    }));
  }

  const active = grants.some((grant) => grant.status === "active");
  const locked = disabled || pending;

  return (
    <section aria-labelledby="autonomy-title" className="order-4 rounded-2xl border border-amber-300 bg-amber-50 p-5 text-slate-900 dark:border-amber-700 dark:bg-slate-900 dark:text-slate-100">
      <h2 id="autonomy-title" className="font-semibold">Autonomous mode Â· {active ? "Grant active" : "Off"}</h2>
      <p className="my-2 text-sm">Autonomous mode lets AURA perform approved actions within the permissions and resource scopes you grant. Actions may modify data. Some external actions cannot be undone.</p>
      <p className="mb-3 text-sm">For this workflow, the available permission is local task creation on one goal. Each run starts when you submit it.</p>
      <label className="flex items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={enabling} disabled={locked || !goals.length} onChange={(event) => setEnabling(event.target.checked)} />
        Set up an autonomous grant
      </label>
      {error && <p role="alert" className="my-2 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
      {enabling && (
        <form onSubmit={enable} className="my-4 grid gap-3 text-sm">
          <label className="grid gap-1">Goal
            <select name="goal" required className="rounded border border-slate-400 p-2 dark:bg-slate-900">
              {goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input name="operation" type="checkbox" required /> Allow AURA to create local tasks
          </label>
          <label className="grid gap-1">Duration in minutes
            <input name="duration" type="number" min={5} max={60} defaultValue={15} required className="rounded border border-slate-400 bg-transparent p-2" />
          </label>
          <label className="grid gap-1">Maximum runs
            <input name="runs" type="number" min={1} max={5} defaultValue={1} required className="rounded border border-slate-400 bg-transparent p-2" />
          </label>
          <label className="grid gap-1">Maximum tasks per run
            <input name="tasks" type="number" min={3} max={8} defaultValue={5} required className="rounded border border-slate-400 bg-transparent p-2" />
          </label>
          <label className="flex items-start gap-2">
            <input name="consent" type="checkbox" required /> I authorize task creation within these limits.
          </label>
          <Button disabled={locked} type="submit" className="bg-blue-600! text-white! hover:bg-blue-700!">Enable grant</Button>
        </form>
      )}
      {grants.some((grant) => grant.status === "active" || grant.status === "paused") && (
        <Button className="mt-3" variant="destructive" disabled={locked} onClick={() => {
          if (!window.confirm("Stop all autonomous task grants for this account?")) return;
          void update(async () => {
          await stopAutonomy();
          return undefined;
        });
        }}>Emergency stop</Button>
      )}
      {!!grants.length && (
        <ul className="my-3 grid gap-3 text-sm">
          {grants.map((grant) => (
            <li key={grant.id} className="rounded border border-slate-300 p-3 dark:border-slate-700">
              <p className="break-words font-medium">{goals.find(({ id }) => id === grant.goal_id)?.title ?? "Unavailable goal"}</p>
              <p className="capitalize">{grant.status.replaceAll("_", " ")} Â· {grant.runs_remaining} runs left</p>
              <p>Expires {new Date(grant.expires_at).toLocaleString()}</p>
              {grant.status === "active" && (
                <label className="my-2 flex items-center gap-2">
                  <input type="checkbox" disabled={locked} checked={selectedGrant === grant.id}
                    onChange={(event) => onSelect(event.target.checked ? grant.id : "")} />
                  Use for the next run
                </label>
              )}
              {(grant.status === "active" || grant.status === "paused") && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" disabled={locked} onClick={() => {
                    const action = grant.status === "active" ? "pause" : "resume";
                    if (action === "pause" && !window.confirm("Pause this autonomous grant?")) return;
                    void update(() => transitionAutonomyGrant(grant.id, action));
                  }}>
                    {grant.status === "active" ? "Pause grant" : "Resume grant"}
                  </Button>
                  <Button size="sm" variant="outline" disabled={locked} onClick={() => {
                    if (window.confirm("Revoke this autonomous grant?")) {
                      void update(() => transitionAutonomyGrant(grant.id, "revoke"));
                    }
                  }}>Revoke</Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
