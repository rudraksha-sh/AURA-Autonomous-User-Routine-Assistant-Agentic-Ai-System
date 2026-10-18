"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { CircleAlert, RefreshCw } from "lucide-react";
import { ApiError, getMe } from "@/services/auth";
import { clearAccessToken, getAccessToken } from "@/services/auth-storage";

function loginHref(destination: string) {
  return `/login?next=${encodeURIComponent(destination)}`;
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isVerified, setIsVerified] = React.useState(false);
  const [isChecking, setIsChecking] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [retryKey, setRetryKey] = React.useState(0);

  React.useEffect(() => {
    let active = true;
    const destination = `${window.location.pathname}${window.location.search}`;
    const redirectToLogin = () => {
      clearAccessToken();
      router.replace(loginHref(destination));
    };
    const handleSessionExpired = () => redirectToLogin();
    const handleStorage = (event: StorageEvent) => {
      if (event.key === "aura_access_token" && !event.newValue) redirectToLogin();
    };

    window.addEventListener("aura:session-expired", handleSessionExpired);
    window.addEventListener("storage", handleStorage);

    async function verifySession() {
      setIsChecking(true);
      setError(null);
      if (!getAccessToken()) {
        redirectToLogin();
        return;
      }

      try {
        await getMe();
        if (active) setIsVerified(true);
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.status === 401) {
          redirectToLogin();
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to verify your session.");
      } finally {
        if (active) setIsChecking(false);
      }
    }

    void verifySession();
    return () => {
      active = false;
      window.removeEventListener("aura:session-expired", handleSessionExpired);
      window.removeEventListener("storage", handleStorage);
    };
  }, [pathname, retryKey, router]);

  if (isVerified) return children;

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      {error ? (
        <section role="alert" className="w-full max-w-md rounded-2xl border border-amber-200 bg-white p-6 text-center shadow-sm">
          <CircleAlert aria-hidden="true" className="mx-auto size-8 text-amber-600" />
          <h1 className="mt-4 text-lg font-semibold text-slate-900">Could not verify your session</h1>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
          <button type="button" onClick={() => setRetryKey((value) => value + 1)} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700">
            <RefreshCw aria-hidden="true" className={`size-4 ${isChecking ? "animate-spin" : ""}`} />Retry
          </button>
        </section>
      ) : (
        <p role="status" className="text-sm text-slate-500">Verifying your session...</p>
      )}
    </main>
  );
}
