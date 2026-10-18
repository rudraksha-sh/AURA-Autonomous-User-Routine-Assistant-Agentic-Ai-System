import { expireAccessToken, getAccessToken } from "@/services/auth-storage";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AssistantToolRequest =
  | { tool: "list_goals" }
  | { tool: "list_tasks" }
  | { tool: "create_goal"; idempotency_key: string; title: string }
  | { tool: "create_task"; idempotency_key: string; goal_id: number; title: string }
  | { tool: "complete_task"; idempotency_key: string; task_id: number };

export type AssistantToolResponse = {
  tool: string;
  goals?: Goal[] | null;
  tasks?: Task[] | null;
  result?: Goal | Task | null;
  replayed: boolean;
};

export class AssistantApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "AssistantApiError";
  }
}

export async function runAssistantTool(request: AssistantToolRequest): Promise<AssistantToolResponse> {
  const token = getAccessToken();
  if (!token) {
    expireAccessToken();
    throw new AssistantApiError("Authentication required.", 401);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/assistant/tools`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(request),
    });
  } catch {
    throw new AssistantApiError("Could not reach AURA. Check your connection and retry.", 0);
  }
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body && typeof body === "object" && "detail" in body
      ? String(body.detail)
      : `Assistant action failed (${response.status}).`;
    throw new AssistantApiError(message, response.status);
  }
  return response.json() as Promise<AssistantToolResponse>;
}
