import ApplicationDetailPage from "@/components/applications/ApplicationDetailPage";

type ApplicationRouteProps = {
  params: Promise<{
    applicationId: string;
  }>;
};

export const metadata = {
  title: "Application | CareerPilot AI",
};

export default async function ApplicationRoute({
  params,
}: ApplicationRouteProps) {
  const { applicationId } = await params;

  return (
    <ApplicationDetailPage
      applicationId={Number(applicationId)}
    />
  );
}
