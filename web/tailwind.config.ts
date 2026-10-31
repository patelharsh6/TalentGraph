import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5", // Deep indigo
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
        violet: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed", // Rich violet
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
        },
        cyan: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4", // Bright cyan accent
          600: "#0891b2",
          700: "#0e7490",
        },
        dark: {
          bg: "#0B0F1A", // Dark theme background
          surface: "#111827", // Card / surface background
          surfaceHover: "#1E293B",
          border: "rgba(255, 255, 255, 0.08)",
          subtle: "rgba(255, 255, 255, 0.04)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        heading: ["var(--font-heading)", "Plus Jakarta Sans", "Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Menlo", "monospace"],
      },
      borderRadius: {
        btn: "12px",
        card: "20px",
        "2xl": "16px",
        "3xl": "20px",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 12px 32px -8px rgba(79,70,229,.08)",
        glow: "0 0 24px -4px rgba(79,70,229,0.35)",
        "glow-cyan": "0 0 24px -4px rgba(6,182,212,0.35)",
        "card-light": "0 1px 3px rgba(15,23,42,0.06), 0 10px 25px -5px rgba(15,23,42,0.04)",
        "card-dark": "0 0 0 1px rgba(255,255,255,0.08), 0 12px 32px -8px rgba(0,0,0,0.5)",
      },
      animation: {
        "float-slow": "float 4s ease-in-out infinite",
        "pulse-subtle": "pulseSubtle 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "shimmer": "shimmer 2s linear infinite",
        "border-glow": "borderGlow 6s ease infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        borderGlow: {
          "0%, 100%": { borderColor: "#4F46E5" },
          "33%": { borderColor: "#7C3AED" },
          "66%": { borderColor: "#06B6D4" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
