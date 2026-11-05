import type { Metadata } from "next";
import { UsagePage } from "@/components/UsagePage";

export const metadata: Metadata = { title: "Utilizare pe echipe" };

export default function UsageRoute() {
  return <UsagePage />;
}
