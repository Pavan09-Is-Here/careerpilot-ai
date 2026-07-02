import ApplicationPrepPage from "@/components/applications/ApplicationPrepPage";

type PrepRouteProps = {
  params: Promise<{
    jobId: string;
  }>;
};

export const metadata = {
  title: "Prepare & Apply | CareerPilot AI",
};

export default async function ApplicationPrepRoute({
  params,
}: PrepRouteProps) {
  const { jobId } = await params;

  return <ApplicationPrepPage jobId={Number(jobId)} />;
}
