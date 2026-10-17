import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        panel: "#13131a",
        "panel-2": "#1a1a24",
        border: "#26262e",
        ink: "#ececf1",
        mute: "#8b8b9a",
        accent: "#8b5cf6",
        "accent-2": "#c026d3",
        good: "#34d399",
        bad: "#f87171",
        warning: "#fbbf24",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
      },
      borderRadius: { sm: "6px", md: "10px", lg: "14px", xl: "20px" },
      boxShadow: {
        glow: "0 0 24px rgba(139, 92, 246, 0.35)",
        "glow-lg": "0 0 48px rgba(139, 92, 246, 0.45)",
      },
    },
  },
  plugins: [],
};
export default config;
