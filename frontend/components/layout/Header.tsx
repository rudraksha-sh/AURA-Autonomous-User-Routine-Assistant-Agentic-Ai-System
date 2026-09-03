import { Bell, Menu, UserRound } from "lucide-react";

type HeaderProps = {
  userName: string;
};

const iconButtonClassName =
  "flex size-10 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2";

export function Header({ userName }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 md:h-20 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-label="Open navigation menu"
          className={`${iconButtonClassName} md:hidden`}
        >
          <Menu aria-hidden="true" className="size-5" />
        </button>

        <h1 className="truncate text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          Dashboard
        </h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          aria-label="View notifications"
          className={iconButtonClassName}
        >
          <Bell aria-hidden="true" className="size-5" />
        </button>

        <div className="flex items-center gap-2 rounded-xl py-1 pl-1 pr-2 sm:gap-3 sm:pr-3">
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
      </div>
    </header>
  );
}
