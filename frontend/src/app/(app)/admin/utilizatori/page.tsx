import type { Metadata } from "next";
import { UsersPage } from "@/components/UsersPage";

export const metadata: Metadata = { title: "Utilizatori" };

export default function UsersRoute() {
  return <UsersPage />;
}
