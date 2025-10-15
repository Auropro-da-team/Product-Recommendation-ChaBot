/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    fontFamily: {
      sans: ['Georgia', 'serif'],
    },
    extend: {
      colors: {
        'primary-blue': 'rgb(146, 179, 202)',
        'primary-orange': 'rgb(243, 195, 177)',
        'main-text': 'rgb(0, 43, 49)',
        'error-red': 'rgb(208, 69, 82)',
      },
      animation: {
        spinner: 'spinner 1.5s linear infinite',
        'spinner-delayed': 'spinner 1.5s linear infinite 0.75s',
        messageFadeIn: 'messageFadeIn 0.5s ease-out',
        botIdle: 'botIdle 1s infinite',
        bounce: "bounce 1.5s infinite",
        scroll: 'scroll 1.5s linear infinite', // ✅ ADDED
      },
      keyframes: {
        spinner: {
          '0%': { transform: 'scale(0)', opacity: 1 },
          '100%': { transform: 'scale(1)', opacity: 0 },
        },
        messageFadeIn: {
          '0%': { opacity: 0, transform: 'scale(0.9)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        botIdle: {
          '0%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
          '100%': { transform: 'translateY(0)' },
        },
        scroll: { // ✅ ADDED
          '0%': { transform: 'translateY(0%)' },
          '100%': { transform: 'translateY(-75%)' },
        },
      },
    },
  },
  plugins: [],
};
