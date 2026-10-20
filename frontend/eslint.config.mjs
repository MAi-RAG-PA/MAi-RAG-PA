// Flat ESLint config for ESLint 9.
// Replaces the legacy src/eslintrc.config, which ESLint never resolved:
// wrong name (no dot), wrong location (inside src/), legacy format (v9 is
// flat-config only), and no lint script existed at all.
import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';

export default [
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**'] },

  js.configs.recommended,

  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      react: reactPlugin,
      'react-hooks': reactHooks,
    },
    settings: { react: { version: 'detect' } },
    rules: {
      // Recommended sets from the installed plugins (verified shapes:
      // typescript-eslint classic rule dicts; react + react-hooks native flat)
      ...tsPlugin.configs.recommended.rules,
      ...tsPlugin.configs['eslint-recommended'].overrides[0].rules,
      ...reactPlugin.configs.flat.recommended.rules,
      ...reactHooks.configs.flat.recommended.rules,

      // -- intent carried over from the legacy src/eslintrc.config --
      'indent': ['warn', 2],
      'semi': ['warn', 'always'],
      'quotes': ['warn', 'single'],
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',

      // -- TypeScript adjustments (standard practice for TSX) --
      'no-undef': 'off',                           // tsc's job
      'no-unused-vars': 'off',                     // replaced by the TS-aware rule below
      '@typescript-eslint/no-unused-vars': 'warn', // legacy "warn" intent, no false positives on type-only imports
      'react/prop-types': 'off',                   // props are typed in TSX
    },
  },
];
