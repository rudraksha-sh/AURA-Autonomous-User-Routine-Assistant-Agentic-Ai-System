"use client";

import { useRouter } from "next/navigation";
import { LogOut, UserRound } from "lucide-react";

import { clearAccessToken } from "@/services/auth-storage";
import { logout } from "@/services/auth";

type HeaderProps = {
  userName: string;
  title?: string;
};

export function Header({ userName, title = "Dashboard" }: HeaderProps) {
  const router = useRouter();

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // Local logout must still complete if the API cannot be reached.
    } finally {
      clearAccessToken();
      router.replace("/login");
    }
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 md:h-20 md:px-8">
      <h1 className="truncate text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">{title}</h1>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="flex min-w-0 items-center gap-2 rounded-xl py-1 pl-1 pr-2 sm:gap-3 sm:pr-3">
          <span
            aria-hidden="true"
            className="flex size-9 items-center justify-center rounded-lg bg-slate-100 text-slate-600"
          >
            <UserRound className="size-5" />
          </span>

          <span className="hidden max-w-40 truncate text-sm font-medium text-slate-700 sm:inline">
            {userName}
          </span>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          aria-label="Log out"
          title="Log out"
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-2 text-sm font-medium text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 sm:px-3"
        >
          <LogOut aria-hidden="true" className="size-4" />
          <span className="hidden sm:inline">Log out</span>
        </button>
      </div>
    </header>
  );
}
