import { defineConfig } from "astro/config";

// ponytail: static-only. No SSR adapter, no Tailwind. Plain CSS for the design tokens.
export default defineConfig({
  output: "static",
  server: { port: 4321 },
});
