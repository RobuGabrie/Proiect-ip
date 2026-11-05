import type { Metadata } from "next";
import { WaitlistPage } from "@/components/WaitlistPage";

export const metadata: Metadata = { title: "Listă de așteptare" };

export default function WaitlistRoute() {
  return <WaitlistPage />;
}
