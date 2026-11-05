import type { Metadata } from "next";
import { ResourceCatalog } from "@/components/ResourceCatalog";

export const metadata: Metadata = { title: "Săli" };

export default function RoomsPage() {
  return <ResourceCatalog tip="SALA" />;
}
