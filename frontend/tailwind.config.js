/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void: '#060a12',      // page background
        panel: '#0b1220',     // cards
        'panel-2': '#0f192b', // nested cards
        line: '#1b2a42',      // borders
        accent: '#22d3ee',    // cyan (primary)
        violet: { 400: '#a78bfa', 500: '#8b5cf6' },
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Menlo', 'monospace'],
      },
      boxShadow: { glow: '0 0 0 1px rgba(34,211,238,.35), 0 0 24px rgba(34,211,238,.15)' },
    },
  },
  plugins: [],
};
