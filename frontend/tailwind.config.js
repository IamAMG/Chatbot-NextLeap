/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        stone: { 50: "#F5F4EE", 100: "#FAF9F5" },
        obsidian: { 900: "#111315", DEFAULT: "#111315" },
        slate: { 600: "#5C6166" },
        emerald: { 500: "#00D09C", 700: "#008A68" },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
}
