import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";
import babelParser from "@babel/eslint-parser";
import prettierPlugin from "eslint-plugin-prettier";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

const isProd = process.env.NODE_ENV === "production";

export default [
  {
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  js.configs.recommended,

  ...vue.configs["flat/recommended"],

  prettierConfig,

  {
    files: ["**/*.vue", "**/*.js", "**/*.jsx", "**/*.cjs", "**/*.mjs"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: babelParser,
        requireConfigFile: false,
        ecmaVersion: 2021,
        sourceType: "module",
      },
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        process: "readonly",
      },
    },

    plugins: {
      vue,
      prettier: prettierPlugin,
    },

    rules: {
      "prettier/prettier": "warn",
      // Environment-based rules
      "no-console": isProd ? "warn" : "off",
      "no-debugger": isProd ? "warn" : "off",

      // Vue deprecations
      "vue/no-deprecated-slot-attribute": "warn",
      "vue/no-deprecated-v-on-native-modifier": "warn",
      "vue/no-deprecated-dollar-listeners-api": "warn",
      "vue/no-deprecated-destroyed-lifecycle": "warn",
      "vue/no-deprecated-dollar-scopedslots-api": "warn",
      "vue/no-deprecated-events-api": "warn",
      "vue/no-deprecated-filter": "warn",
      "vue/no-deprecated-functional-template": "warn",
      "vue/no-deprecated-html-element-is": "warn",
      "vue/no-deprecated-inline-template": "warn",
      "vue/no-deprecated-props-default-this": "warn",
      "vue/no-deprecated-scope-attribute": "warn",
      "vue/no-deprecated-v-bind-sync": "warn",
      "vue/no-deprecated-v-is": "warn",
      "vue/no-lifecycle-after-await": "warn",
      "vue/no-watch-after-await": "warn",

      // Vue best practices
      "vue/require-explicit-emits": "warn",
      "vue/multi-word-component-names": "warn",
      "vue/no-v-for-template-key-on-child": "error",
      "vue/no-v-model-argument": "off",

      "vue/no-unused-components": "warn",
      "vue/no-unused-vars": "warn",
    },
  },
];
