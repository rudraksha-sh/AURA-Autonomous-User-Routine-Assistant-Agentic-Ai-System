"use client";

import * as React from "react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { getMe } from "@/services/auth";
import type { User } from "@/types/auth";

export default function DashboardPage() {
  const [user, setUser] = React.useState<User | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    let isMounted = true;

    async function loadUser() {
      try {
        const currentUser = await getMe();

        if (isMounted) {
          setUser(currentUser);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load your account."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">Loading your dashboard...</p>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Unable to load dashboard
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            {error ?? "Authentication required."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header userName={user.name} />

        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Good morning, {user.name}
            </h2>

            <p className="mt-2 text-sm text-slate-500 sm:text-base">
              Here&apos;s what&apos;s happening with your routine today.
            </p>
          </div>

          <section
            aria-labelledby="dashboard-ready-heading"
            className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:mt-10 sm:p-8"
          >
            <h3
              id="dashboard-ready-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Your dashboard is ready.
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Goals, tasks, and routine insights will appear here.
            </p>
          </section>
        </main>
      </div>
    </div>
  );
}
