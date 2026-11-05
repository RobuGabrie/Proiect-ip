import type { Metadata } from "next";
import { ApprovalsPage } from "@/components/ApprovalsPage";

export const metadata: Metadata = { title: "Aprobări" };

export default function ApprovalsRoute() {
  return <ApprovalsPage />;
}
