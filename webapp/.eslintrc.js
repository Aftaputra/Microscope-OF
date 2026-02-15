module.exports = {
  root: true,
  env: {
    node: true,
    es2021: true,
  },
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@babel/eslint-parser",
    requireConfigFile: false,
    ecmaVersion: 2021,
    sourceType: "module",
  },
  extends: ["plugin:vue/vue3-recommended", "eslint:recommended", "@vue/prettier"],
  rules: {
    "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",

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

    "vue/require-explicit-emits": "warn", // Require emits declaration
    "vue/multi-word-component-names": "warn", // Component naming
    "vue/no-v-for-template-key-on-child": "error", // Key placement
    "vue/no-v-model-argument": "off", // Allow v-model arguments (Vue 3 feature)

    "vue/no-unused-components": "warn",
    "vue/no-unused-vars": "warn",
  },
};
