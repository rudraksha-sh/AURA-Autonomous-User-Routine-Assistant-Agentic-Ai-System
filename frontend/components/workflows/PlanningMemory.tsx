"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { deleteMemory, listMemories, type MemoryEntry, saveMemory } from "@/services/planner";

export function PlanningMemory({ className, fieldClassName }: { className: string; fieldClassName: string }) {
  const [items, setItems] = useState<MemoryEntry[] | null>(null);
  const [editing, setEditing] = useState<MemoryEntry | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function act(operation: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await operation();
      setItems(await listMemories());
      setEditing(null);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not update planning memory.");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void act(async () => {
      await saveMemory({
        text: String(values.get("text")), use_for_planning: values.has("planning"),
        retention_days: Number(values.get("retention")),
      }, editing?.id);
      form.reset();
    });
  }

  return (
    <section className={className}>
      <h2 className="text-lg font-semibold">Planning memory</h2>
      {error && <p role="alert" className="mt-2 text-sm">{error}</p>}
      {items === null ? (
        <Button className="mt-2" variant="outline" disabled={busy} onClick={() => void act(async () => {})}>Manage memories</Button>
      ) : (
        <>
          <ul className="space-y-2 text-sm">
            {items.map((item) => (
              <li key={item.id} className="break-words">
                <p>{item.text}</p>
                <p>Expires {new Date(item.expires_at).toLocaleDateString()}</p>
                <Button variant="ghost" disabled={busy} onClick={() => setEditing(item)}>Edit</Button>
                <Button variant="ghost" disabled={busy} onClick={() => void act(() => deleteMemory(item.id))}>Delete</Button>
              </li>
            ))}
          </ul>
          <form key={editing?.id ?? "new"} onSubmit={submit} className="mt-3 grid gap-2 text-sm">
            <label>{editing ? "Edit memory" : "New memory"}<textarea name="text" className={fieldClassName} required maxLength={500} defaultValue={editing?.text} /></label>
            <label>Keep for days<input name="retention" type="number" className={fieldClassName} min={1} max={90} defaultValue={30} required /></label>
            <label className="flex gap-2"><input type="checkbox" name="planning" defaultChecked={editing?.use_for_planning} /> Allow use in planning</label>
            <Button type="submit" disabled={busy}>{editing ? "Save changes" : "Save memory"}</Button>
            {editing && <Button type="button" variant="outline" disabled={busy} onClick={() => setEditing(null)}>Cancel edit</Button>}
            {items.length > 0 && <Button type="button" variant="outline" disabled={busy} onClick={() => {
              if (window.confirm("Delete all your planning memories?")) void act(() => deleteMemory());
            }}>Reset memories</Button>}
          </form>
        </>
      )}
    </section>
  );
}
