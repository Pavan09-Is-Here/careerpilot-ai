"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import PasswordInput from "@/components/auth/PasswordInput";
import { resetPassword } from "@/lib/api";
import { clearAuthToken } from "@/lib/auth";

export default function ResetPassword() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const missingToken = token.length === 0;

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, newPassword);
      // Any stale session is invalid after a reset.
      clearAuthToken();
      setNewPassword("");
      setDone(true);
    } catch (resetError) {
      setError(
        resetError instanceof Error
          ? resetError.message
          : "This reset link is invalid or has expired.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-md">
        <Link
          href="/auth"
          className="text-sm font-medium text-violet-600 transition hover:text-violet-700"
        >
          ← Account
        </Link>
        <h1 className="mt-3 text-2xl font-bold text-slate-900">
          Reset password
        </h1>

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="mt-6 cp-card p-5">
          <h2 className="cp-eyebrow text-xs tracking-wide">
            Choose a new password
          </h2>

          {done ? (
            <>
              <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                Your password has been reset. Please sign in with your new
                password.
              </div>
              <Link
                href="/auth"
                className="mt-4 block w-full rounded-lg bg-violet-600 px-4 py-2 text-center text-sm font-semibold text-white transition hover:bg-violet-500"
              >
                Go to sign in
              </Link>
            </>
          ) : missingToken ? (
            <p className="mt-3 text-sm text-red-700">
              This reset link is missing its token. Request a new one from
              the sign-in page.
            </p>
          ) : (
            <>
              <PasswordInput
                value={newPassword}
                onChange={setNewPassword}
                placeholder="New password (min 8 chars)"
                autoComplete="new-password"
              />
              <button
                type="button"
                disabled={busy || newPassword.length < 8}
                onClick={() => void submit()}
                className="mt-3 w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
              >
                Reset password
              </button>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
