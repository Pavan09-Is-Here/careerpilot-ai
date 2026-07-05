"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  getCandidateProfile,
  getDocuments,
  getJobSources,
  getSession,
} from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

type Step = {
  key: string;
  label: string;
  done: boolean;
  href: string;
};

function CheckIcon() {
  return (
    <svg
      className="h-5 w-5 text-emerald-600"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m5 13 4 4L19 7"
      />
    </svg>
  );
}

function TodoCircle() {
  return (
    <span
      aria-hidden="true"
      className="block h-5 w-5 rounded-full border-2 border-slate-300"
    />
  );
}

export default function GettingStarted() {
  const [loading, setLoading] = useState(true);
  const [loggedOut, setLoggedOut] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    // Logged-out visitors must not trigger authed requests.
    if (!getAuthToken()) {
      queueMicrotask(() => {
        setLoggedOut(true);
        setLoading(false);
      });
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    async function loadChecklist() {
      // Each request is independent; a failure should mark that step
      // as todo rather than crash the whole checklist.
      const [session, profile, documents, sources] =
        await Promise.all([
          getSession(controller.signal).catch(() => null),
          getCandidateProfile().catch(() => null),
          getDocuments(controller.signal).catch(() => null),
          getJobSources(1, 1, controller.signal).catch(
            () => null,
          ),
        ]);

      if (cancelled) {
        return;
      }

      const nextSteps: Step[] = [
        {
          key: "account",
          label: "Create your account",
          done: Boolean(session?.authenticated),
          href: "/auth",
        },
        {
          key: "profile",
          label: "Add your profile",
          done: Boolean(
            profile && profile.full_name.trim() !== "",
          ),
          href: "/profile",
        },
        {
          key: "cv",
          label: "Upload your CV",
          done: Boolean(documents && documents.length > 0),
          href: "/documents",
        },
        {
          key: "verify_details",
          label: "Verify your details",
          done: Boolean(profile?.facts_verified),
          href: "/profile",
        },
        {
          key: "board",
          label: "Connect a company board",
          done: Boolean(sources && sources.items.length > 0),
          href: "/job-sources",
        },
      ];

      setSteps(nextSteps);
      setLoading(false);
    }

    void loadChecklist();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  if (loggedOut) {
    return (
      <section className="cp-card border-violet-200 bg-violet-50/60">
        <h2 className="text-xl font-semibold text-slate-900">
          Create your account to get started
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 cp-muted">
          Sign in or create an account to build your verified
          facts vault, upload your CV, and discover matching
          roles.
        </p>
        <Link href="/auth" className="cp-btn-primary mt-4">
          Sign in or create account
        </Link>
      </section>
    );
  }

  const doneCount = steps.filter((step) => step.done).length;

  return (
    <section className="cp-card border-violet-200 bg-violet-50/60">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <p className="cp-eyebrow">Getting started</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">
            Set up CareerPilot
          </h2>
        </div>
        {!loading ? (
          <span className="cp-chip">
            {doneCount} of {steps.length} done
          </span>
        ) : null}
      </div>

      {loading ? (
        <p className="mt-4 text-sm cp-muted">
          Checking your setup…
        </p>
      ) : (
        <ol className="mt-5 grid gap-2">
          {steps.map((step) => (
            <li key={step.key}>
              <Link
                href={step.href}
                className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm transition hover:border-violet-400 hover:shadow-sm"
              >
                <span className="shrink-0">
                  {step.done ? <CheckIcon /> : <TodoCircle />}
                </span>
                <span
                  className={
                    step.done
                      ? "text-slate-500 line-through"
                      : "font-medium text-slate-800"
                  }
                >
                  {step.label}
                </span>
                <span className="ml-auto text-xs font-medium text-violet-700">
                  {step.done ? "Review" : "Start"}
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
