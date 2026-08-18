import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Dashboard — AURA",
  description: "Your AURA routine dashboard.",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-50 md:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <Header />

        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 md:px-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Good morning, User
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
