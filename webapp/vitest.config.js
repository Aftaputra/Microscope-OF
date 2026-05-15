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
    css: false,
    pool: 'forks',
    singleThread: true,

    define: {
      __VUE_PROD_DEVTOOLS__: false,
    },

    coverage: {
      provider: 'v8',
      clean: true,
      cleanOnStart: true,
    },

    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: ['@mui/material', 'lucide-react'], // Add your largest component dependencies here
        },
      },
    },

    environment: "happy-dom",

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
