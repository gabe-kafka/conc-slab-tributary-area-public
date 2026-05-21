import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
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
            <span className="text-accent font-semibold tracking-wide uppercase">
              Tributary
            </span>
            <span className="text-text-muted">/</span>
            <span>Concrete Slab</span>
          </div>
          <StatusClock />
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
