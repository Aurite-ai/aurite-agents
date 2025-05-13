/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // Removed safelist for now to simplify
  theme: {
    extend: { // Key change: use extend for colors
      colors: {
        'dracula-background': '#282a36',
        'dracula-foreground': '#f8f8f2',
        'dracula-current-line': '#44475a',
        'dracula-comment': '#6272a4',
        'dracula-cyan': '#8be9fd',      // Added for completeness from typical Dracula
        'dracula-green': '#50fa7b',
        'dracula-orange': '#ffb86c',    // Added
        'dracula-pink': '#ff79c6',
        'dracula-purple': '#bd93f9',
        'dracula-red': '#ff5555',       // Added
        'dracula-yellow': '#f1fa8c',    // Added
      },
    },
  },
  plugins: [],
}
