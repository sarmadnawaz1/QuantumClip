/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Desktop app's exact color scheme from CustomTkinter
        primary: {
          DEFAULT: '#3B8ED0',  // Main blue from desktop
          50: '#E3F2FD',
          100: '#BBDEFB',
          200: '#90CAF9',
          300: '#64B5F6',
          400: '#42A5F5',
          500: '#3B8ED0',  // Desktop primary
          600: '#1F6AA5',  // Desktop dark mode primary
          700: '#144870',  // Desktop hover dark
          800: '#0D3A5A',
          900: '#072540',
          hover: '#36719F',  // Desktop hover color
        },
        gray: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#EEEEEE',
          300: '#E0E0E0',
          400: '#BDBDBD',
          500: '#9E9E9E',
          600: '#757575',
          700: '#616161',
          800: '#424242',
          900: '#212121',
          // Desktop specific grays
          light: '#EBEBEB',  // gray92
          frame: '#DBDBDB',  // gray86
          dark: '#242424',   // gray14
          darkFrame: '#2B2B2B', // gray17
        },
      },
      fontFamily: {
        sans: ['Roboto', 'SF Display', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'desktop': '6px',  // Desktop corner radius
      },
    },
  },
  plugins: [],
}

