// vite.config.mjs

// Vite replaces Vue CLI as the build tool for Vue 3.
// Note: Comments are generated to explain relevant configuration options.

import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import purgecss from "@fullhuman/postcss-purgecss";

// https://vitejs.dev/config/
export default defineConfig({
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
    // OFM uses port 5000, so we avoid conflicts. run, and override by using the address:
    // http://microscope.local:8080/?overrideOrigin=http://microscope.local:5000#
    port: 8080,
    strictPort: true,
  },
  css: {
    preprocessorOptions: {
      less: {
        math: "always",
        relativeUrls: true,
        javascriptEnabled: true,
      },
    },
    postcss: {
      plugins:
        process.env.NODE_ENV === "production"
          ? [
              purgecss({
                content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
                safelist: {
                  standard: [
                    "html",
                    "body",
                    "svg",
                    "path",
                    "g",
                    "canvas",
                    // Add dynamic UIkit states that JS toggles
                    "uk-active",
                    "uk-open",
                    "uk-modal-page",
                    "uk-offcanvas-page",
                    "uk-preserve-width",
                  ],
                  deep: [
                    // Protect UIkit attribute selectors (e.g., [uk-modal])
                    /\[uk-[^\]]+\]/,
                    /\[data-uk-[^\]]+\]/,
                    // Protect Vue transitions
                    /-(leave|enter|appear)(|-(to|from|active))$/,
                    // Protect UIkit dynamic components (notifications, tooltips, sorting)
                    /^uk-notification/,
                    /^uk-tooltip/,
                    /^uk-animation-/,
                    /^uk-transition-/,
                  ],
                  // Notice we completely removed the "greedy" block!
                },
              }),
            ]
          : [],
    },
  },
});
