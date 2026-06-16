/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        muted: "#64748B",
        line: "#E2E8F0",
        panel: "#F8FAFC",
        brand: "#0F3D4A",
        accent: "#10B981",
        highlight: "#A3E635",
        mint: "#DDF7EC"
      }
    },
  },
  plugins: [],
};
