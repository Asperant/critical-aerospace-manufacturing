import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  { ignores: ["dist", "node_modules", "coverage"] },
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ["vite.config.ts", "eslint.config.js"],
    languageOptions: { globals: globals.node },
  },
]);
