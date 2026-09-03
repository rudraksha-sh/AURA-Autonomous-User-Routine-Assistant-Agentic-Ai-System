import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Create an account — AURA",
  description: "Create your AURA account.",
};

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-xl font-bold text-white">
            A
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Create an account
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Start building your routine with AURA.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <RegisterForm />
        </div>
      </div>
    </main>
  );
}