"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { getSession, logout } from "@/lib/api";
import { clearAuthToken, getAuthToken } from "@/lib/auth";
import type { AuthSession } from "@/types/auth";

const PRIMARY_LINKS: { label: string; href: string }[] = [
  { label: "Dashboard", href: "/" },
  { label: "Profile", href: "/profile" },
  { label: "Documents", href: "/documents" },
  { label: "Jobs", href: "/jobs" },
  { label: "Applications", href: "/applications" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function LogoMark() {
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-white">
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 19V6m0 0 7 4m-7-4L5 10"
        />
      </svg>
    </span>
  );
}

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(
    null,
  );
  const [checked, setChecked] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Only touch authed endpoints when a token is present; a logged-out
    // visitor must be able to view public pages without a forced redirect.
    if (!getAuthToken()) {
      queueMicrotask(() => setChecked(true));
      return;
    }

    const controller = new AbortController();

    queueMicrotask(() => {
      getSession(controller.signal)
        .then((result) => {
          setSession(result);
        })
        .catch(() => {
          // Tolerate failures silently; nav still renders a Sign in link.
        })
        .finally(() => {
          setChecked(true);
        });
    });

    return () => controller.abort();
    // Re-check the session when the route changes (e.g. after signing in).
  }, [pathname]);

  // Close the account menu on outside click.
  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function handleClick(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () =>
      document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
    } catch {
      // Even if the server call fails, clear the local token below.
    } finally {
      clearAuthToken();
      setSession(null);
      setMenuOpen(false);
      setSigningOut(false);
      router.push("/auth");
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 text-base font-medium text-slate-900"
        >
          <LogoMark />
          CareerPilot
        </Link>

        <div className="flex flex-wrap items-center gap-1">
          {PRIMARY_LINKS.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-violet-50 text-violet-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-violet-700"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <div className="ml-auto">
          {!checked ? (
            <span className="text-sm text-slate-400">…</span>
          ) : session ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:border-violet-400 hover:text-violet-700"
              >
                <span className="max-w-[10rem] truncate">
                  {session.username}
                </span>
                <svg
                  className="h-4 w-4 text-slate-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m6 9 6 6 6-6"
                  />
                </svg>
              </button>

              {menuOpen ? (
                <div
                  role="menu"
                  className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
                >
                  <Link
                    href="/auth"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-50 hover:text-violet-700"
                  >
                    Account
                  </Link>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleSignOut}
                    disabled={signingOut}
                    className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-slate-50 hover:text-violet-700 disabled:opacity-50"
                  >
                    {signingOut ? "Signing out…" : "Sign out"}
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <Link
              href="/auth"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:border-violet-400 hover:text-violet-700"
            >
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
