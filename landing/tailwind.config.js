/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'red-brand':  '#E8420A',
        'red-hover':  '#C23308',
        'red-tint':   '#FFF1EE',
        'red-tint2':  '#FFE8E0',
        'text-pri':   '#0A0A0A',
        'text-sec':   '#6B7280',
        'border-col': '#E5E7EB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}


