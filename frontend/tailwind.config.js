/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Investa Real Estate corporate palette — deep petrol / teal.
        investa: {
          950: "#08222C",
          900: "#0B2D3A",
          800: "#0E3B4C", // primary dark (header / sidebar)
          700: "#13495C",
          600: "#1C5A70",
          500: "#2A7088", // accent
          400: "#4C8FA6",
          300: "#8FB8C6",
          sand: "#C8A15A", // restrained gold highlight
          // legacy aliases (kept so older class names still resolve)
          dark: "#0E3B4C",
          accent: "#2A7088",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      letterSpacing: {
        widest2: "0.22em",
      },
      boxShadow: {
        card: "0 1px 2px rgba(8, 34, 44, 0.06), 0 8px 24px rgba(8, 34, 44, 0.05)",
      },
    },
  },
  plugins: [],
};
