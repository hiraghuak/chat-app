import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API calls to the FastAPI backend so the frontend always
// uses same-origin relative paths (/api, /health) — identical to production,
// where FastAPI serves the built SPA. No CORS handling needed in either case.
const BACKEND = process.env.VITE_BACKEND_URL || "http://localhost:7860";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/health": { target: BACKEND, changeOrigin: true },
    },
  },
  build: { outDir: "dist" },
});
