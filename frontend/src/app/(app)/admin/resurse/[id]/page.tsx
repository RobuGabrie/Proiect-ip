import { ResourceSettings } from "@/components/ResourceSettings";

export default async function ResourceSettingsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ResourceSettings key={id} resourceId={id} />;
}
