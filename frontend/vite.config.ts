import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend origin for the dev/preview proxy. Override when port 8000 is taken, e.g.
// VITE_PROXY_TARGET=http://127.0.0.1:8001 npm run dev
const target = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target,
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    proxy: {
      "/api": { target, changeOrigin: false },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});
