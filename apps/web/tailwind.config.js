/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        forest: {
          50: "#f0faf4",
          100: "#d1f0de",
          200: "#a3e1bd",
          300: "#6dcc97",
          400: "#3db373",
          500: "#1e9655",
          600: "#157a44",
          700: "#126238",
          800: "#104e2d",
          900: "#0d3f25",
        },
      },
    },
  },
  plugins: [],
};
