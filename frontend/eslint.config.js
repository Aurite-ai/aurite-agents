import js from '@eslint/js';
import prettier from 'eslint-plugin-prettier';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';

export default [
  js.configs.recommended,
  {
    files: ['**/*.js', '**/*.ts', '**/*.tsx'],
    plugins: {
      prettier,
      '@typescript-eslint': tseslint,
    },
    languageOptions: {
      parser: tsparser,
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        global: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',
        // Browser globals
        fetch: 'readonly',
        TextDecoder: 'readonly',
        AbortSignal: 'readonly',
        AbortController: 'readonly',
        Response: 'readonly',
        Request: 'readonly',
        Headers: 'readonly',
        HeadersInit: 'readonly',
        RequestInit: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLButtonElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLParagraphElement: 'readonly',
        HTMLHeadingElement: 'readonly',
        HTMLTextAreaElement: 'readonly',
        HTMLElement: 'readonly',
        Element: 'readonly',
        Event: 'readonly',
        MouseEvent: 'readonly',
        KeyboardEvent: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        location: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        confirm: 'readonly',
        alert: 'readonly',
        prompt: 'readonly',
        // Node.js globals
        NodeJS: 'readonly',
      },
    },
    rules: {
      // General JavaScript/TypeScript rules
      'no-console': 'off', // Allow console statements for development
      'no-debugger': 'error',
      'no-alert': 'warn', // Downgrade from error to warning
      'no-var': 'error',
      'prefer-const': 'error',
      'prefer-template': 'error',
      'object-shorthand': 'error',
      'no-duplicate-imports': 'error',
      'no-useless-rename': 'error',
      'no-useless-computed-key': 'error',
      'no-useless-constructor': 'error',
      'no-useless-return': 'error',
      'no-else-return': 'error',
      'no-lonely-if': 'error',
      'no-unneeded-ternary': 'error',
      'no-nested-ternary': 'warn', // Downgrade from error to warning
      'no-unused-vars': 'off', // Temporarily disabled to unblock development
      'prefer-arrow-callback': 'error',
      'arrow-body-style': ['error', 'as-needed'],
      'curly': ['error', 'all'],
      'eqeqeq': ['error', 'always'],
      'no-param-reassign': 'error',
      'no-return-assign': 'error',
      'no-sequences': 'error',
      'no-throw-literal': 'error',
      'no-unused-expressions': 'error',
      'no-useless-catch': 'warn', // Downgrade from error to warning
      'radix': 'error',
      'yoda': 'error',

      // Prettier integration
      'prettier/prettier': 'error',
    },
  },
  {
    files: ['tests/**/*.ts', '**/*.test.ts', '**/*.spec.ts', 'examples/**/*.ts', 'scripts/**/*.ts'],
    rules: {
      'no-console': 'off',
    },
  },
];
