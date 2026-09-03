import Link from "next/link";
import {
  CheckSquare,
  CircleGauge,
  Flag,
  Settings,
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
  { href: "/tasks", icon: CheckSquare, label: "Tasks" },
];

const settingsItem: NavigationItem = {
  href: "/settings",
  icon: Settings,
  label: "Settings",
};

function NavigationLink({ href, icon: Icon, label }: NavigationItem) {
  return (
    <Link
      href={href}
      className="group flex min-w-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:bg-slate-100 focus-visible:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
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
        <ul className="flex gap-1 overflow-x-auto md:flex-col">
          {navigationItems.map((item) => (
            <li key={item.href} className="shrink-0 md:w-full">
              <NavigationLink {...item} />
            </li>
          ))}
        </ul>
      </nav>

      <nav
        aria-label="Account navigation"
        className="border-t border-slate-200 px-3 py-3 md:mt-auto md:border-0 md:px-4 md:py-6"
      >
        <NavigationLink {...settingsItem} />
      </nav>
    </aside>
  );
}
