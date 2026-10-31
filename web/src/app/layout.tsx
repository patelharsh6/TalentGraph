import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Inter } from "next/font/google";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Toaster } from "sonner";
import "./globals.css";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const heading = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

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
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${sans.variable} ${heading.variable} min-h-screen flex flex-col bg-slate-50 dark:bg-dark-bg text-slate-900 dark:text-slate-100 transition-colors duration-200 antialiased`}
      >
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {/* Subtle dot-grid texture on entire page */}
          <div className="fixed inset-0 bg-dot-grid opacity-60 dark:opacity-40 pointer-events-none -z-10" />

          {/* Sticky Glass Navbar */}
          <Navbar />

          {/* Main page view */}
          <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 relative z-10">
            {children}
          </main>

          {/* Modern Minimal Footer */}
          <Footer />

          {/* Toast notifications */}
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{
              className: "font-sans text-xs rounded-xl border dark:border-white/10 shadow-lg",
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
