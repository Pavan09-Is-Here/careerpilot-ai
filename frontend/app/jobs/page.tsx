import { Suspense } from "react";

import JobDiscoveryPage from "@/components/jobs/JobDiscoveryPage";

export const metadata = {
  title: "Job Discovery | CareerPilot AI",
};

export default function JobsPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-5xl px-6 py-10">
          <p className="text-sm text-slate-500">Loading…</p>
        </main>
      }
    >
      <JobDiscoveryPage />
    </Suspense>
  );
}
