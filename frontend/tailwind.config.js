/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        muted: "#64748b",
        line: "#d8dee8",
        panel: "#f7f9fc",
        brand: "#0f766e"
      }
    },
  },
  plugins: [],
};
