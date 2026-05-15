// File: vitest.config.js
// Generic configuration for vitest

import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "path";

console.log("\n\n::: Reading vitest config.");

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          hoistStatic: false,
        },
      },
    }),
  ],

  test: {
    environment: "jsdom",

    globals: true,

    server: {
      deps: {
        inline: ["vue", "@vue/test-utils", "pinia", "@pinia/testing"],
      },
    },
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      vue: path.resolve(__dirname, "./node_modules/vue"),
    },
  },
});
