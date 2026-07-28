import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "katex/dist/katex.min.css";
import Sidebar from "@/components/Sidebar";
import Providers from "@/components/Providers";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "pyFOOMB",
  description: "Bioprocess Modelling Framework",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetBrainsMono.variable}`}>
      <body className="flex min-h-screen flex-col md:flex-row">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5 md:max-h-screen">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
