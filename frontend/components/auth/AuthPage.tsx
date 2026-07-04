"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  changePassword,
  getAuthStatus,
  getSession,
  isAbortError,
  login,
  logout,
  register,
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

const inputClass =
  "mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200";

export default function AuthPage() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // "login" or "register" for the logged-out view.
  const [mode, setMode] = useState<"login" | "register">("login");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);

    try {
      // Keep /status for connectivity, but the UI no longer gates on it:
      // registration is always available.
      await getAuthStatus(signal);

      if (getAuthToken()) {
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

  const resetCredentialFields = () => {
    setUsername("");
    setPassword("");
    setFullName("");
    setEmail("");
  };

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-md">
        <Link
          href="/"
          className="text-sm font-medium text-violet-600 transition hover:text-violet-700"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-3 text-2xl font-bold text-slate-900">Account</h1>

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {notice && (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {notice}
          </div>
        )}

        {loading ? (
          <p className="mt-6 text-sm text-slate-500">Loading…</p>
        ) : session ? (
          <>
            <section className="mt-6 cp-card p-5">
              <h2 className="cp-eyebrow text-xs tracking-wide">
                Signed in
              </h2>
              <dl className="mt-3 space-y-1 text-sm text-slate-600">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Username</dt>
                  <dd>{session.username}</dd>
                </div>
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
                className="mt-4 w-full rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 transition hover:border-violet-400 hover:text-violet-700"
              >
                Sign out
              </button>
            </section>

            <section className="mt-6 cp-card p-5">
              <h2 className="cp-eyebrow text-xs tracking-wide">
                Change password
              </h2>
              <input
                type="password"
                value={currentPassword}
                onChange={(event) =>
                  setCurrentPassword(event.target.value)
                }
                placeholder="Current password"
                className={inputClass}
              />
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="New password (min 8 chars)"
                className={inputClass}
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
                    setNotice("Password changed. Please sign in again.");
                    await refresh();
                  })
                }
                className="mt-3 w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
              >
                Change password
              </button>
            </section>
          </>
        ) : mode === "register" ? (
          <section className="mt-6 cp-card p-5">
            <h2 className="cp-eyebrow text-xs tracking-wide">
              Create account
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Pick a username and password. Your profile and data are
              private to your account.
            </p>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Username (letters, numbers, . _ -)"
              autoComplete="username"
              className={inputClass}
            />
            <input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Full name"
              className={inputClass}
            />
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Email"
              autoComplete="email"
              className={inputClass}
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password (min 8 chars)"
              autoComplete="new-password"
              className={inputClass}
            />
            <button
              type="button"
              disabled={
                busy ||
                username.trim().length < 3 ||
                password.length < 8 ||
                fullName.trim().length < 1 ||
                email.trim().length < 3
              }
              onClick={() =>
                run(async () => {
                  const result = await register({
                    username: username.trim(),
                    password,
                    full_name: fullName.trim(),
                    email: email.trim(),
                  });
                  setAuthToken(result.token);
                  resetCredentialFields();
                  setNotice(`Welcome, ${result.username}. Account created.`);
                  await refresh();
                })
              }
              className="mt-3 w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              Create account
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
                setNotice(null);
              }}
              className="mt-3 w-full text-center text-sm font-medium text-violet-600 transition hover:text-violet-700"
            >
              Already have an account? Sign in
            </button>
          </section>
        ) : (
          <section className="mt-6 cp-card p-5">
            <h2 className="cp-eyebrow text-xs tracking-wide">
              Sign in
            </h2>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Username"
              autoComplete="username"
              className={inputClass}
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              autoComplete="current-password"
              className={inputClass}
            />
            <button
              type="button"
              disabled={
                busy || username.trim().length < 1 || password.length < 1
              }
              onClick={() =>
                run(async () => {
                  const result = await login(username.trim(), password);
                  setAuthToken(result.token);
                  resetCredentialFields();
                  setNotice("Signed in.");
                  await refresh();
                })
              }
              className="mt-3 w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setError(null);
                setNotice(null);
              }}
              className="mt-3 w-full text-center text-sm font-medium text-violet-600 transition hover:text-violet-700"
            >
              New here? Create an account
            </button>
          </section>
        )}
      </div>
    </main>
  );
}
