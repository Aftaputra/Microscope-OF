// stylelint.config.mjs
export default {
  extends: ["stylelint-config-standard"],

  overrides: [
    {
      files: ["**/*.vue"],
      customSyntax: "postcss-html",
    },
    {
      files: ["**/*.less"],
      customSyntax: "postcss-less",
    },
  ],

  rules: {
    // UIKit class naming doesn't match Stylelint's default class pattern
    "selector-class-pattern": null,
    // Less @import is fine
    "no-invalid-position-at-import-rule": null,
    "no-empty-source": null,
  },
};
