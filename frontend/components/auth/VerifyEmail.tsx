"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { verifyEmail } from "@/lib/api";

type Status = "pending" | "success" | "error";

export default function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [status, setStatus] = useState<Status>(
    token ? "pending" : "error",
  );
  const [message, setMessage] = useState<string>(
    token
      ? "Verifying your email address…"
      : "This verification link is missing its token.",
  );
  const started = useRef(false);

  useEffect(() => {
    if (started.current || !token) {
      return;
    }
    started.current = true;

    const controller = new AbortController();
    void (async () => {
      try {
        const result = await verifyEmail(token, controller.signal);
        setStatus("success");
        setMessage(result.message);
      } catch (verifyError) {
        setStatus("error");
        setMessage(
          verifyError instanceof Error
            ? verifyError.message
            : "This verification link is invalid or has expired.",
        );
      }
    })();

    return () => controller.abort();
  }, [token]);

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
          Verify email
        </h1>

        <section className="mt-6 cp-card p-5">
          <h2 className="cp-eyebrow text-xs tracking-wide">
            Email verification
          </h2>
          {status === "pending" && (
            <p className="mt-3 text-sm text-slate-500">{message}</p>
          )}
          {status === "success" && (
            <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {message}
            </div>
          )}
          {status === "error" && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {message}
            </div>
          )}
          <Link
            href="/auth"
            className="mt-4 block w-full rounded-lg bg-violet-600 px-4 py-2 text-center text-sm font-semibold text-white transition hover:bg-violet-500"
          >
            Go to account
          </Link>
        </section>
      </div>
    </main>
  );
}
