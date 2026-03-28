import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Digest",
  description: "Three snapshots a day. High-signal AI updates.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
