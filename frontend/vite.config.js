import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    // 开发环境禁用 PWA,避免 Service Worker 拦截 SSE 流式请求
    VitePWA({
      disabled: mode === 'development',
      registerType: 'autoUpdate',
      manifest: {
        name: '面试私教 Agent',
        short_name: '面试私教',
        description: '一对一 AI 面试指导,帮你拿到高薪 offer',
        theme_color: '#4f46e5',
        background_color: '#0f172a',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="40" fill="%234f46e5"/><text x="96" y="130" font-size="100" text-anchor="middle" fill="white">面</text></svg>',
            sizes: '192x192',
            type: 'image/svg+xml'
          },
          {
            src: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="100" fill="%234f46e5"/><text x="256" y="350" font-size="280" text-anchor="middle" fill="white">面</text></svg>',
            sizes: '512x512',
            type: 'image/svg+xml'
          }
        ]
      }
    })
  ],
  server: {
    // host: true 让开发服务器开放局域网访问,手机连同一 WiFi 即可通过电脑 IP 访问
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE 流式响应需要禁用缓冲,确保 chunk 实时转发
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const ct = proxyRes.headers['content-type'] || ''
            if (ct.includes('text/event-stream')) {
              // 禁用代理层缓冲,确保 SSE 数据实时转发
              proxyRes.headers['X-Accel-Buffering'] = 'no'
              proxyRes.headers['Cache-Control'] = 'no-cache'
              proxyRes.headers['Connection'] = 'keep-alive'
            }
          })
        }
      }
    }
  }
}))
