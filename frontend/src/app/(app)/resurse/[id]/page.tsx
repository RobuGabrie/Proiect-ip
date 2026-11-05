import { ResourceCalendar } from "@/components/ResourceCalendar";

export default async function ResourcePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ResourceCalendar key={id} resourceId={id} />;
}
