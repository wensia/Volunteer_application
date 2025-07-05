// Tailwind CSS CDN配置
// 用于替代CDN版本，提供本地化的样式
window.tailwindConfig = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
      }
    }
  }
}