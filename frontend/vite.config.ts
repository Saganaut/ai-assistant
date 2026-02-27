import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: ["kev-desktop.tail9a5e2f.ts.net"],
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
  build: {
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
      },
      format: {
        comments: false,
      },
    },
  },
});
