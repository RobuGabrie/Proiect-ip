import type { Metadata } from "next";
import { CategoriesPage } from "@/components/CategoriesPage";

export const metadata: Metadata = { title: "Categorii" };

export default function CategoriesRoute() {
  return <CategoriesPage />;
}
