import type { Metadata } from "next";
import { ProfilePage } from "@/components/ProfilePage";

export const metadata: Metadata = { title: "Profil" };

export default function ProfileRoute() {
  return <ProfilePage />;
}
