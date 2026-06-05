import type { Metadata } from "next";
import Link from "next/link";
import { JetBrains_Mono } from "next/font/google";
import { AuthControls } from "@/components/AuthControls";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Concrete Slab Tributary Area",
  description: "Two-way slab tributary area calculator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${mono.variable} h-full`}>
      <body className="min-h-full flex flex-col font-mono">
        <header className="h-8 flex items-center justify-between px-3 border-b border-border-panel bg-bg-surface text-text-secondary text-[11px]">
          <div className="flex items-center gap-3">
            <Link
              href="/?upload=1"
              className="text-accent font-semibold tracking-wide uppercase hover:text-accent-hover transition-colors"
            >
              Tributary
            </Link>
            <span className="text-text-muted">/</span>
            <span>Concrete Slab</span>
          </div>
          <div className="flex items-center gap-3">
            <AuthControls />
            <StatusClock />
          </div>
        </header>
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}

function StatusClock() {
  return (
    <span className="text-text-muted" suppressHydrationWarning>
      v1.0
    </span>
  );
}
