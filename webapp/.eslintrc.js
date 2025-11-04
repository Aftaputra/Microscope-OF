module.exports = {
  root: true,

  env: {
    node: true,
  },

  parser: "vue-eslint-parser",

  parserOptions: {
    parser: "@babel/eslint-parser",
    requireConfigFile: false,
    ecmaVersion: 2020,
    sourceType: "module",
  },

  extends: ["plugin:vue/recommended", "eslint:recommended", "@vue/prettier"],

  rules: {
    "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
  },
};
