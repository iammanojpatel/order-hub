import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "App", template: "%s · App" },
  description: "Production-grade Next.js + FastAPI reference application",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
