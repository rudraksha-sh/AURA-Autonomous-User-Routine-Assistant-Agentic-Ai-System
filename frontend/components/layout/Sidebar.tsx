"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CircleGauge,
  Flag,
  ListTodo,
  Plus,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

type NavigationItem = {
  href: string;
  icon: LucideIcon;
  label: string;
};

const navigationItems: NavigationItem[] = [
  { href: "/dashboard", icon: CircleGauge, label: "Dashboard" },
  { href: "/goals", icon: Flag, label: "Goals" },
  { href: "/tasks", icon: ListTodo, label: "Tasks" },
];

function NavigationLink({ href, icon: Icon, label, isActive }: NavigationItem & { isActive: boolean }) {
  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={`group flex min-w-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}
    >
      <Icon
        aria-hidden="true"
        className="size-5 shrink-0 text-slate-400 transition-colors group-hover:text-slate-700 group-focus-visible:text-slate-700"
      />
      <span className="truncate">{label}</span>
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="border-slate-200 bg-white md:flex md:min-h-screen md:w-64 md:flex-col md:border-r">
      <div className="flex h-16 items-center border-b border-slate-200 px-4 md:h-20 md:border-0 md:px-6">
        <Link
          href="/dashboard"
          aria-label="AURA dashboard"
          className="flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
        >
          <span
            aria-hidden="true"
            className="flex size-10 items-center justify-center rounded-xl bg-slate-900 text-lg font-bold text-white shadow-sm"
          >
            A
          </span>
          <span className="text-lg font-bold tracking-tight text-slate-900">
            AURA
          </span>
        </Link>
      </div>

      <nav aria-label="Primary navigation" className="px-3 py-3 md:px-4 md:py-6">
        <p className="mb-2 hidden px-3 text-[11px] font-semibold tracking-[0.16em] text-slate-400 uppercase md:block">
          Workspace
        </p>
        <ul className="flex gap-1 overflow-x-auto md:flex-col">
          {navigationItems.map((item) => (
            <li key={item.href} className="shrink-0 md:w-full">
              <NavigationLink {...item} isActive={pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`))} />
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex items-center gap-2 px-3 pb-3 md:block md:px-4 md:pb-0">
        <Link
          href="/goals"
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 md:w-full"
        >
          <Plus aria-hidden="true" className="size-4" />
          Create a goal
        </Link>
      </div>

      <div className="hidden md:mt-auto md:block md:p-4">
        <div className="rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
          <span className="flex size-9 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm ring-1 ring-blue-100">
            <Sparkles aria-hidden="true" className="size-4" />
          </span>
          <p className="mt-3 text-sm font-semibold text-slate-900">
            Small steps add up
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Give your goals a clear next step and a realistic deadline.
          </p>
        </div>
      </div>
    </aside>
  );
}
