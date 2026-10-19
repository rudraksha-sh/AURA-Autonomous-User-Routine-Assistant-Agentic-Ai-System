import { expireAccessToken, getAccessToken } from "@/services/auth-storage";

export async function downloadAccountExport(format: "json" | "csv") {
  const token = getAccessToken();
  if (!token) { expireAccessToken(); throw new Error("Authentication required."); }
  const response = await fetch(`/api/profile/export?format=${format}`, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Export failed (${response.status}).`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = format === "json" ? "aura-export.json" : "aura-export.csv";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function deleteAccount() {
  const token = getAccessToken();
  if (!token) { expireAccessToken(); throw new Error("Authentication required."); }
  const response = await fetch("/api/profile/account", {
    method: "DELETE",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ confirmation: "DELETE" }),
  });
  if (response.status === 401) expireAccessToken();
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Account deletion failed (${response.status}).`);
  }
  expireAccessToken();
}
