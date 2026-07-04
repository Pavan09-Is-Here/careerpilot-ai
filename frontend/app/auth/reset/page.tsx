import { Suspense } from "react";

import ResetPassword from "@/components/auth/ResetPassword";

export const metadata = {
  title: "Reset password | CareerPilot AI",
};

export default function ResetPasswordRoute() {
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
      <ResetPassword />
    </Suspense>
  );
}
