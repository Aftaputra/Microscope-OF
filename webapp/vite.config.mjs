// vite.config.mjs

// Vite replaces Vue CLI as the build tool for Vue 3.
// Note: Comments are generated to explain relevant configuration options.

import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import purgecss from '@fullhuman/postcss-purgecss';

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
        // Always include math in Less files.
        math: "always",
        // Enable relative URLs in Less files.
        relativeUrls: true,
        // Enable JavaScript in Less files
        javascriptEnabled: true,
      },
    },
    postcss: {
      plugins: [
        purgecss({
          content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
          safelist: {
            standard: ['html', 'body'], // Keep basic HTML elements
            greedy: [ // greedy works by matching patterns, so we can keep all classes starting with 'uk-' for UIkit
              /^uk-/, // Keep all classes starting with 'uk-' (UIkit)
            ]
          },
        }),
      ],
    },
  },
});
