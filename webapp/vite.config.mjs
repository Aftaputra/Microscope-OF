// vite.config.mjs

// Vite replaces Vue CLI as the build tool for Vue 3.
// Note: Comments are generated to explain relevant configuration options.

import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  var target;

  if (command === "serve") {
    if (env.VITE_API_TARGET === "local") {
      target = "http://localhost:5000";
    } else if (env.VITE_API_TARGET === "microscope") {
      target = env.VITE_MICROSCOPE_HOST || "http://microscope.local:5000";
    } else {
      throw new Error(`Invalid VITE_API_TARGET: ${env.VITE_API_TARGET}`);
    }
    // Allow a console log as we were serving for development.
    // eslint-disable-next-line no-console
    console.log(`Proxying /api → ${target}`);
  }

  return {
    plugins: [vue()],

    build: {
      // Output directory for production builds
      outDir: "../src/openflexure_microscope_server/static",
      // Clear output directory before build
      emptyOutDir: true,
      chunkSizeWarningLimit: 400,
      rollupOptions: {
        output: {
          manualChunks: {
            "vue-vendor": ["vue", "pinia", "pinia-plugin-persistedstate"],
            openseadragon: ["openseadragon"],
            uikit: ["uikit"],
            utils: ["axios", "mitt", "mousetrap", "@vueuse/core"],
          },
        },
      },
    },

    resolve: {
      alias: {
        // Setup path alias for src directory.
        // This allows importing modules using '@/path/to/module'.
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
      // Recognize these file extensions for module resolution.
      extensions: [".mjs", ".js", ".ts", ".jsx", ".tsx", ".json", ".vue"],
    },
    server: {
      host: true,
      // Set the development server port to 8080.
      port: 8080,
      strictPort: true,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
        },
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          // Always include math in Less files.
          math: "always",
          // Enable relative URLs in Less files.
          relativeUrls: true,
          // Enable JavaScript in Less files
          javascriptEnabled: true,
        },
      },
    },
  };
});
