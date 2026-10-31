import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Navbar from "@/components/Navbar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TalentGraph | Semantic Resume Parsing & Talent Intelligence",
  description:
    "Production-grade semantic resume parsing, ESCO/O*NET skill normalization, explainable job matching, and career coaching.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100`}>
        <Navbar />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
        <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>
              <span>TalentGraph Enterprise Pipeline v0.1.0</span> •{" "}
              <span>Built with FastAPI & Next.js</span>
            </div>
            <div className="flex items-center gap-4">
              <a href="/about" className="hover:text-indigo-600 dark:hover:text-indigo-400">Architecture</a>
              <a href="/evaluation" className="hover:text-indigo-600 dark:hover:text-indigo-400">Benchmarks</a>
              <a href="/healthz" target="_blank" className="hover:text-indigo-600 dark:hover:text-indigo-400">System Health</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

