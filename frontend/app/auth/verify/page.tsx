import { Suspense } from "react";

import VerifyEmail from "@/components/auth/VerifyEmail";

export const metadata = {
  title: "Verify email | CareerPilot AI",
};

export default function VerifyEmailRoute() {
  return (
    <Suspense
      fallback={
        <main className="cp-page">
          <div className="mx-auto max-w-md">
            <p className="mt-6 text-sm text-slate-500">Loading…</p>
          </div>
        </main>
      }
    >
      <VerifyEmail />
    </Suspense>
  );
}
