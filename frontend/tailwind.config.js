/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Display',
          'SF Pro Text',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
      colors: {
        // 扣子风格暖色系 - 奶油/大地色调（更淡雅的版本）
        warm: {
          50: '#fdfcfa',
          100: '#faf7f2',
          150: '#f5f0e8',
          200: '#ede6da',
          250: '#e2d8c8',
          300: '#d4c8b4',
          400: '#c5b89f',
          500: '#b0a088',
          600: '#9a8a74',
          700: '#827564',
          800: '#6b6054',
          900: '#554d44',
        },
        // 棕色系强调色
        brown: {
          50: '#fdf8f0',
          100: '#f5e6d0',
          200: '#e8c9a0',
          300: '#d4a574',
          400: '#c2884d',
          500: '#a07040',
          600: '#8a5e34',
          700: '#724c2a',
          800: '#5c3d22',
          900: '#463018',
        },
        // 星空渐变色系 (参考扣子背景的深邃感)
        cosmos: {
          deep: '#1a1226',
          purple: '#3d2868',
          blue: '#1e4d8c',
          gold: '#c9a84c',
        },
      },
      borderRadius: {
        'card': '20px',
        'card-lg': '28px',
        'card-xl': '36px',
      },
      boxShadow: {
        'card': '0 4px 24px rgba(139, 105, 20, 0.08)',
        'card-hover': '0 8px 32px rgba(139, 105, 20, 0.12)',
        'card-lg': '0 12px 48px rgba(139, 105, 20, 0.1)',
        'soft': '0 2px 8px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04)',
        'soft-lg': '0 8px 32px rgba(0, 0, 0, 0.08), 0 16px 64px rgba(0, 0, 0, 0.06)',
      },
      transitionTimingFunction: {
        'warm': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'warm-out': 'cubic-bezier(0, 0, 0.2, 1)',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        messageAppear: {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.6s ease-out forwards',
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-down': 'slideDown 0.3s ease-out forwards',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 3s ease-in-out infinite',
        'message-appear': 'messageAppear 0.4s ease-out forwards',
      },
      backgroundImage: {
        'warm-gradient': 'linear-gradient(180deg, #faf8f5 0%, #f5f0e8 50%, #ede5d8 100%)',
        'cosmos-gradient': 'linear-gradient(135deg, #1a1226 0%, #3d2868 25%, #1e4d8c 75%, #1a1226 100%)',
        'gold-gradient': 'linear-gradient(135deg, #c9a84c 0%, #8B6914 50%, #c9a84c 100%)',
      },
    },
  },
  plugins: [],
};
