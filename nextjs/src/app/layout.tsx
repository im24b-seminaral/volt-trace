import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import Header from "@/components/Header";
import SessionHeartbeat from "@/components/SessionHeartbeat";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "VoltTrace",
  description: "SDAT- und ESL-Messdaten erkunden und exportieren",
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/android-chrome-192x192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de-CH" className={cn("font-sans", geist.variable)}>
      <body>
        <SessionHeartbeat />
        <Header />
        {children}
      </body>
    </html>
  );
}
