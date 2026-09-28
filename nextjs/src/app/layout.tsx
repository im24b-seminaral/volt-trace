import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Volt Trace",
  description: "SDAT- und ESL-Messdaten erkunden und exportieren",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de-CH">
      <body>{children}</body>
    </html>
  );
}
