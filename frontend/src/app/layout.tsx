import type { Metadata } from "next";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Resource Manager",
  description: "Programarea resurselor de cercetare din universitate",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ro">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
