import type { Metadata } from "next";
import { ResourceCatalog } from "@/components/ResourceCatalog";

export const metadata: Metadata = { title: "Echipamente" };

export default function EquipmentPage() {
  return <ResourceCatalog tip="ECHIPAMENT" />;
}
