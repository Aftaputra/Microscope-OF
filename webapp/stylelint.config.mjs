// stylelint.config.mjs
export default {
  // This applies standard CSS rules to the whole project by default
  extends: ["stylelint-config-standard"],

  overrides: [
    {
      files: ["**/*.vue"],
      customSyntax: "postcss-html",
      // If you write <style lang="less"> inside Vue components and get 
      // the same error there, uncomment the rule below:
      // rules: { "declaration-property-value-no-unknown": null }
    },
    {
      files: ["**/*.less"],
      customSyntax: "postcss-less",
      // THIS IS THE FIX: Tell Stylelint to apply LESS-specific 
      // rules (which ignore @ variables) only to these files.
      extends: ["stylelint-config-standard-less"], 
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