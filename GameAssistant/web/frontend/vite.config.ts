import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // Vue core
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Ant Design Vue - separate chunk for UI library
          'ant-design': ['ant-design-vue'],
          // ECharts - separate chunk for charting library (largest dependency)
          'echarts': ['echarts', 'vue-echarts'],
          // VueUse utilities
          'vueuse': ['@vueuse/core'],
          // Axios
          'axios': ['axios'],
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    // Warn when chunk is larger than 500KB
    chunkSizeWarningLimit: 500,
  },
  // Optimization
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'ant-design-vue', 'axios'],
  },
})
