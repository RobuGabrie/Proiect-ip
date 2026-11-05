import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import { Ambient } from "@/components/Ambient";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: { default: "Research Resource Manager", template: "%s | Research Resource Manager" },
  description: "Programarea sălilor și a echipamentelor de cercetare din universitate.",
};

export const viewport: Viewport = {
  themeColor: "#0E3A44",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ro" className={sans.variable}>
      <body>
        <Ambient />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
