import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: rootDir,
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    // Vite's default binds IPv6 loopback only on Windows, so http://127.0.0.1:5173
    // refused connections while http://localhost worked. Binding "::" is
    // dual-stack and accepts both, which also removes the cold-start 404s.
    host: "::",
    warmup: { clientFiles: ["./src/main.tsx"] },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      // Explicit entry point: avoids Vite's "could not auto-determine entry
      // point" cold-start warning that preceded the dev-server 404.
      input: fileURLToPath(new URL("./index.html", import.meta.url)),
    },
  },
});