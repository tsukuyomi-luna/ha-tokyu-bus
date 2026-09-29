import js from "@eslint/js";
import globals from "globals";
export default [
  { ignores: ["node_modules/**", ".venv/**"] },
  js.configs.recommended,
  { files: ["www/**/*.js"], languageOptions: { globals: globals.browser } },
  {
    files: ["tests/**/*.cjs"],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
];
