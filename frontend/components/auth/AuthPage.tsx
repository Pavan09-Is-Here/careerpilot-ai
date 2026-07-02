"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  changePassword,
  getAuthStatus,
  getSession,
  isAbortError,
  login,
  logout,
  setupPassword,
} from "@/lib/api";
import {
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from "@/lib/auth";

import type { AuthSession } from "@/types/auth";

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString();
}

export default function AuthPage() {
  const [configured, setConfigured] = useState<boolean | null>(
    null,
  );
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);

    try {
      const status = await getAuthStatus(signal);
      setConfigured(status.configured);

      if (status.configured && getAuthToken()) {
        try {
          setSession(await getSession(signal));
        } catch {
          clearAuthToken();
          setSession(null);
        }
      } else {
        setSession(null);
      }
    } catch (refreshError) {
      if (isAbortError(refreshError)) {
        return;
      }
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Could not reach the server.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void refresh(controller.signal);
    });
    return () => controller.abort();
  }, [refresh]);

  const run = useCallback(
    async (action: () => Promise<void>) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await action();
      } catch (actionError) {
        setError(
          actionError instanceof Error
            ? actionError.message
            : "Action failed.",
        );
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-md">
        <Link
          href="/"
          className="text-sm text-blue-300 hover:text-blue-200"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-3 text-2xl font-bold">Account</h1>

        {error && (
          <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
        {notice && (
          <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {notice}
          </div>
        )}

        {loading ? (
          <p className="mt-6 text-sm text-slate-400">Loading…</p>
        ) : configured === false ? (
          <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Set a password
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              Choose a password (at least 8 characters) to secure your
              account.
            </p>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="New password"
              className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
            />
            <button
              type="button"
              disabled={busy || password.length < 8}
              onClick={() =>
                run(async () => {
                  await setupPassword(password);
                  setPassword("");
                  setNotice("Password set. You can now log in.");
                  await refresh();
                })
              }
              className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
            >
              Set password
            </button>
          </section>
        ) : session ? (
          <>
            <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Signed in
              </h2>
              <dl className="mt-3 space-y-1 text-sm text-slate-300">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Session expires</dt>
                  <dd>{formatDateTime(session.expires_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Last used</dt>
                  <dd>{formatDateTime(session.last_used_at)}</dd>
                </div>
              </dl>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await logout();
                    clearAuthToken();
                    setSession(null);
                    setNotice("Signed out.");
                  })
                }
                className="mt-4 w-full rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-blue-400"
              >
                Sign out
              </button>
            </section>

            <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Change password
              </h2>
              <input
                type="password"
                value={currentPassword}
                onChange={(event) =>
                  setCurrentPassword(event.target.value)
                }
                placeholder="Current password"
                className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
              <input
                type="password"
                value={newPassword}
                onChange={(event) =>
                  setNewPassword(event.target.value)
                }
                placeholder="New password (min 8 chars)"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
              <button
                type="button"
                disabled={
                  busy ||
                  currentPassword.length < 1 ||
                  newPassword.length < 8
                }
                onClick={() =>
                  run(async () => {
                    await changePassword(currentPassword, newPassword);
                    setCurrentPassword("");
                    setNewPassword("");
                    clearAuthToken();
                    setSession(null);
                    setNotice(
                      "Password changed. Please sign in again.",
                    );
                    await refresh();
                  })
                }
                className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
              >
                Change password
              </button>
            </section>
          </>
        ) : (
          <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Sign in
            </h2>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
            />
            <button
              type="button"
              disabled={busy || password.length < 1}
              onClick={() =>
                run(async () => {
                  const result = await login(password);
                  setAuthToken(result.token);
                  setPassword("");
                  setNotice("Signed in.");
                  await refresh();
                })
              }
              className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
            >
              Sign in
            </button>
          </section>
        )}
      </div>
    </main>
  );
}
