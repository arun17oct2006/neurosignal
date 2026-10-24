// @lovable.dev/vite-tanstack-config already includes the following, do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools, tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// Additional config can be passed to defineConfig below.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  server: { port: 8080 },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (SSR error wrapper).
    server: { entry: "server" },
  },
});