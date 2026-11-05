import type { Metadata } from "next";
import { MyReservations } from "@/components/MyReservations";

export const metadata: Metadata = { title: "Rezervările mele" };

export default function ReservationsPage() {
  return <MyReservations />;
}
