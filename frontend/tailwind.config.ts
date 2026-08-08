/** @type {import('tailwindcss').Config} */
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "var(--color-primary)",
          hover: "var(--color-primary-hover)",
        },
        secondary: "var(--color-secondary)",
        background: "var(--color-background)",
        surface: {
          DEFAULT: "var(--color-surface)",
          muted: "var(--color-surface-muted)",
        },
        border: "var(--color-border)",
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          disabled: "var(--color-text-disabled)",
        },
        "on-primary": "var(--color-on-primary)",
        success: {
          DEFAULT: "var(--color-success)",
          bg: "var(--color-success-bg)",
        },
        info: {
          DEFAULT: "var(--color-info)",
          bg: "var(--color-info-bg)",
        },
        warning: {
          DEFAULT: "var(--color-warning)",
          bg: "var(--color-warning-bg)",
        },
        danger: {
          DEFAULT: "var(--color-danger)",
          bg: "var(--color-danger-bg)",
        },
      },
      fontFamily: {
        heading: ["Capriola", "sans-serif"],
        body: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
      },
      fontSize: {
        display: ["36px", { lineHeight: "1.1", letterSpacing: "-0.01em" }],
        h1: ["28px", { lineHeight: "1.2", letterSpacing: "-0.01em" }],
        h2: ["22px", { lineHeight: "1.25" }],
        h3: ["18px", { lineHeight: "1.3" }],
        body: ["16px", { lineHeight: "1.6" }],
        small: ["14px", { lineHeight: "1.5" }],
        tiny: ["12px", { lineHeight: "1.4" }],
      },
      spacing: {
        // 8px rhythm — Tailwind's default 4px scale already covers these,
        // but these named steps map to the DESIGN.md scale for clarity.
        section: "96px",
      },
      borderRadius: {
        interactive: "6px",
        container: "12px",
      },
      boxShadow: {
        // one subtle elevation, for modals/dropdowns only — never a glow
        overlay: "0 4px 16px rgba(42, 44, 38, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;