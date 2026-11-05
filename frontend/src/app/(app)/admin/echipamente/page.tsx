import type { Metadata } from "next";
import { AdminResources } from "@/components/AdminResources";

export const metadata: Metadata = { title: "Administrare echipamente" };

export default function AdminEquipmentPage() {
  return <AdminResources tip="ECHIPAMENT" />;
}
