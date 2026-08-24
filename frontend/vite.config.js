import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API calls to the FastAPI server on :8000. In prod, FastAPI
// serves the built files, so the API is same-origin and no proxy is needed.
const API = ["/chat", "/me", "/health", "/ops", "/proposals"];

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    proxy: Object.fromEntries(
      API.map((p) => [p, { target: "http://127.0.0.1:8000", changeOrigin: true }])
    ),
  },
});
