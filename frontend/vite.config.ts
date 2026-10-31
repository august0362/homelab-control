import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".");
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      proxy: {
        // Keep the browser's Host: the backend's CSRF and WebSocket Origin checks compare it
        // with Origin. (The string shorthand would set changeOrigin: true and rewrite Host.)
        // ws: the remote desktop bridge at /api/desktop/ws.
        "/api": { target: env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000", changeOrigin: false, ws: true },
      },
    },
  };
});
