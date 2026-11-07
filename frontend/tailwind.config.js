/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
    theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--bg) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        surface2: 'rgb(var(--surface2) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        line: 'rgb(var(--line) / <alpha-value>)',
        teal: { DEFAULT: 'rgb(var(--teal) / <alpha-value>)', soft: 'rgb(var(--teal-soft) / <alpha-value>)' },
        saffron: { DEFAULT: 'rgb(var(--saffron) / <alpha-value>)', soft: 'rgb(var(--saffron-soft) / <alpha-value>)' },
        onteal: 'rgb(var(--on-teal) / <alpha-value>)',
        leaf: 'rgb(var(--leaf) / <alpha-value>)',
        trust: 'rgb(var(--trust) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        display: ['Fraunces', 'Georgia', 'serif'],
      },
      boxShadow: { card: '0 1px 2px rgb(0 0 0 / 0.04), 0 4px 16px -6px rgb(0 0 0 / 0.08)' },
    },
  },
  plugins: [],
}
