import { UserRound } from "lucide-react";

type HeaderProps = {
  userName: string;
  title?: string;
};

export function Header({ userName, title = "Dashboard" }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 md:h-20 md:px-8">
      <h1 className="truncate text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">{title}</h1>

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
    </header>
  );
}
