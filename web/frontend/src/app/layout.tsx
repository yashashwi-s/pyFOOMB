import type { Metadata } from "next";
import "./globals.css";
import "katex/dist/katex.min.css";
import Sidebar from "@/components/Sidebar";
import Providers from "@/components/Providers";

export const metadata: Metadata = {
  title: "pyFOOMB",
  description: "Bioprocess Modelling Framework",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body style={{ display: "flex", minHeight: "100vh" }}>
        <Providers>
          <Sidebar />
          <main style={{ flex: 1, padding: "20px 24px", overflowY: "auto", maxHeight: "100vh" }}>
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}

