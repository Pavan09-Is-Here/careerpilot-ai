import DocumentDetailPage from "@/components/documents/DocumentDetailPage";

type DocumentRouteProps = {
  params: Promise<{
    documentId: string;
  }>;
};

export const metadata = {
  title: "Document Detail | CareerPilot AI",
};

export default async function DocumentRoute({
  params,
}: DocumentRouteProps) {
  const { documentId } = await params;

  return (
    <DocumentDetailPage
      documentId={Number(documentId)}
    />
  );
}
