import JobDetailPage from "@/components/jobs/JobDetailPage";

type JobRouteProps = {
  params: Promise<{
    jobId: string;
  }>;
};

export const metadata = {
  title: "Job Detail | CareerPilot AI",
};

export default async function JobRoute({
  params,
}: JobRouteProps) {
  const { jobId } = await params;

  return <JobDetailPage jobId={Number(jobId)} />;
}
