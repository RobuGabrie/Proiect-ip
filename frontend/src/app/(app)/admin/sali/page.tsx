import type { Metadata } from "next";
import { AdminResources } from "@/components/AdminResources";

export const metadata: Metadata = { title: "Administrare săli" };

export default function AdminRoomsPage() {
  return <AdminResources tip="SALA" />;
}
