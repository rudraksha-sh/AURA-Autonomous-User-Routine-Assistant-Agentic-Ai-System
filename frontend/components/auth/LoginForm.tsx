"use client";

import * as React from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Alert, AlertDescription } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { loginSchema, type LoginSchema } from "@/lib/validations/auth";

import { useRouter } from "next/navigation";
import { setAccessToken } from "@/services/auth-storage";

import { ApiError, login, verifyLoginOtp } from "@/services/auth";
import { OtpInput } from "@/components/auth/OtpInput";

export function LoginForm({ redirectTo }: { redirectTo?: string }) {
  const router = useRouter();
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [challengeId, setChallengeId] = React.useState<string | null>(null);
  const [otp, setOtp] = React.useState("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginSchema) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await login(data);
      if (response.requires_otp && response.challenge_id) {
        setChallengeId(response.challenge_id);
        setOtp("");
        return;
      }
      if (!response.access_token) throw new Error("The sign-in response was incomplete.");
      completeLogin(response.access_token);
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_verified") {
        const email = encodeURIComponent(data.email);
        router.replace(`/verify-email?email=${email}`);
        return;
      }
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const completeLogin = (token: string) => {
    setAccessToken(token);
    let destination = "/dashboard";
    if (redirectTo?.startsWith("/")) {
      const safeUrl = new URL(redirectTo, "https://aura.local");
      if (safeUrl.origin === "https://aura.local" && safeUrl.pathname !== "/login") {
        destination = `${safeUrl.pathname}${safeUrl.search}${safeUrl.hash}`;
      }
    }
    router.replace(destination);
  };

  const submitOtp = async () => {
    if (!challengeId || otp.length !== 6) return;
    setError(null);
    setIsLoading(true);
    try {
      const response = await verifyLoginOtp({ challenge_id: challengeId, code: otp });
      completeLogin(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to verify the code.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5"
      noValidate
    >
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!challengeId && <div className="space-y-2">
        <Label htmlFor="email">Email</Label>

        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          aria-invalid={errors.email ? "true" : "false"}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />

        {errors.email && (
          <p
            id="email-error"
            className="text-sm text-red-600"
            role="alert"
          >
            {errors.email.message}
          </p>
        )}
      </div>}

      {!challengeId && <div className="space-y-2">
        <Label htmlFor="password">Password</Label>

        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          aria-invalid={errors.password ? "true" : "false"}
          aria-describedby={
            errors.password ? "password-error" : undefined
          }
          {...register("password")}
        />

        {errors.password && (
          <p
            id="password-error"
            className="text-sm text-red-600"
            role="alert"
          >
            {errors.password.message}
          </p>
        )}
      </div>}

      {challengeId && <div className="space-y-4">
        <p className="text-sm text-slate-600">Enter the sign-in code sent to your email.</p>
        <OtpInput value={otp} onChange={setOtp} disabled={isLoading} />
      </div>}

      <Button
        type={challengeId ? "button" : "submit"}
        onClick={challengeId ? () => void submitOtp() : undefined}
        className="w-full"
        disabled={isLoading || (Boolean(challengeId) && otp.length !== 6)}
      >
        {isLoading ? (
          <>
            <Loader2
              className="h-4 w-4 animate-spin"
              aria-hidden="true"
            />
            Signing in...
          </>
        ) : (
          challengeId ? "Verify and sign in" : "Sign in"
        )}
      </Button>

      {!challengeId && <p className="text-right text-sm"><Link href="/forgot-password" className="font-medium text-slate-700 underline underline-offset-4">Forgot password?</Link></p>}
      {challengeId && <button type="button" onClick={() => { setChallengeId(null); setOtp(""); }} className="w-full text-sm text-slate-600 underline underline-offset-4">Back to password sign in</button>}

      <p className="text-center text-sm text-slate-500">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium text-slate-900 underline-offset-4 hover:underline"
        >
          Create one
        </Link>
      </p>
    </form>
  );
}
