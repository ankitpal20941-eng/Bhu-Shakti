/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        ink: "var(--ink)",
        muted: "var(--ink-muted)",
        line: "var(--line)",
        forest: "var(--forest)",
        "forest-soft": "var(--forest-soft)",
        charcoal: "var(--charcoal)",
        slate: "var(--slate)",
        subtle: "var(--blue)",
        safe: "var(--risk-safe)",
        watch: "var(--risk-watch)",
        warning: "var(--risk-warning)",
        critical: "var(--risk-critical)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      borderRadius: { xl: "10px", "2xl": "14px" },
      boxShadow: {
        card: "0 1px 2px rgba(18, 32, 24, 0.06), 0 1px 3px rgba(18, 32, 24, 0.04)",
        panel: "0 8px 30px rgba(18, 32, 24, 0.10)",
      },
      fontSize: {
        "2xs": ["11px", "15px"],
        xs: ["12px", "17px"],
        sm: ["13px", "19px"],
        base: ["14px", "21px"],
        lg: ["16px", "23px"],
        xl: ["19px", "26px"],
        "2xl": ["23px", "30px"],
        "3xl": ["28px", "34px"],
      },
    },
  },
  plugins: [],
};
