import CVVersionDetailPage from "@/components/cv-versions/CVVersionDetailPage";

type CVVersionRouteProps = {
  params: Promise<{
    versionId: string;
  }>;
};

export const metadata = {
  title: "CV Version Detail | CareerPilot AI",
};

export default async function CVVersionRoute({
  params,
}: CVVersionRouteProps) {
  const { versionId } = await params;

  return (
    <CVVersionDetailPage
      versionId={Number(versionId)}
    />
  );
}
