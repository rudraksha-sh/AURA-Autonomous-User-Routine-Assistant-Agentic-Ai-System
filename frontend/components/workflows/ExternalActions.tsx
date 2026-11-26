"use client";

import { type FormEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  listExternalActions, previewExternalAction, transitionExternalAction,
  type ActionOperation, type ExternalAction,
} from "@/services/planner";

export function ExternalActions({ goalId, className, field }: { goalId: number; className: string; field: string }) {
  const [actions, setActions] = useState<ExternalAction[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<{ fingerprint: string; id: string }>(null);

  async function act(operation: () => Promise<ExternalAction[]>) {
    setBusy(true);
    setError("");
    try {
      setActions(await operation());
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to update the sandbox action.");
    } finally {
      setBusy(false);
    }
  }

  function preview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void act(async () => {
      const start = new Date(String(data.get("start"))).toISOString();
      const duration = Number(data.get("duration"));
      const fingerprint = JSON.stringify([goalId, start, duration]);
      if (pending.current?.fingerprint !== fingerprint) pending.current = { fingerprint, id: crypto.randomUUID() };
      const result = await previewExternalAction(pending.current.id, goalId, start, duration);
      pending.current = null;
      return [result, ...(actions ?? []).filter((action) => action.id !== result.id)];
    });
  }

  function move(action: ExternalAction, operation: ActionOperation) {
    void act(async () => {
      if (operation === "confirm" && !window.confirm(
        `${action.effect} at ${new Date(action.payload.start_at).toLocaleString()} for ${action.payload.duration_minutes} minutes. This authorizes one action.`,
      )) return actions ?? [];
      if (operation === "revoke" && !window.confirm("Revoke this action before it is dispatched?")) return actions ?? [];
      const changed = await transitionExternalAction(action, operation);
      return (actions ?? []).map((entry) => entry.id === changed.id ? changed : entry);
    });
  }

  return (
    <section className={className}>
      <h2 className="text-lg font-semibold">External action sandbox</h2>
      {error && <p role="alert" className="text-sm">{error}</p>}
      <Button variant="outline" disabled={busy} onClick={() => void act(listExternalActions)}>
        {actions ? "Refresh actions" : "View and preview actions"}
      </Button>
      {actions && (
        <>
          <form onSubmit={preview} className="mt-3 grid gap-2 text-sm">
            <label>Hold start (device time)<input name="start" className={field} type="datetime-local" required /></label>
            <label>Duration in minutes<input name="duration" className={field} type="number" min={5} max={120} defaultValue={30} required /></label>
            <Button type="submit" disabled={busy || !goalId}>Preview hold for selected goal</Button>
          </form>
          <ul className="mt-3 space-y-3 text-sm">
            {actions.filter((action) => action.goal_id === goalId).map((action) => (
              <li key={action.id} className="space-y-1">
                <p>{action.effect}</p>
                <p>{new Date(action.payload.start_at).toLocaleString()} · {action.payload.duration_minutes} minutes</p>
                <p role="status" className="capitalize">{action.state} · Consent {action.consent}</p>
                {!action.adapter_available && <p>Sandbox dispatch is unavailable.</p>}
                <div className="flex flex-wrap gap-1">
                  {action.state === "preview" && action.consent === "off" &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "confirm")}>Confirm one hold</Button>}
                  {action.state === "queued" && action.consent === "active" &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "pause")}>Pause</Button>}
                  {action.state === "queued" && action.consent === "paused" &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "resume")}>Resume</Button>}
                  {(action.state === "preview" || action.state === "queued" || action.state === "dispatching") &&
                    action.consent !== "revoked" &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "revoke")}>Revoke</Button>}
                  {action.state === "queued" && action.consent === "active" && action.adapter_available &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "dispatch")}>Dispatch confirmed hold</Button>}
                  {(action.state === "unknown" || action.state === "dispatching") && action.adapter_available &&
                    <Button variant="outline" disabled={busy} onClick={() => move(action, "reconcile")}>Check provider outcome</Button>}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
