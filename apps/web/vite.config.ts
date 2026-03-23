import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        { src: path.resolve(__dirname, '../../node_modules/cesium/Build/Cesium/Workers'), dest: 'cesium' },
        { src: path.resolve(__dirname, '../../node_modules/cesium/Build/Cesium/ThirdParty'), dest: 'cesium' },
        { src: path.resolve(__dirname, '../../node_modules/cesium/Build/Cesium/Assets'), dest: 'cesium' },
        { src: path.resolve(__dirname, '../../node_modules/cesium/Build/Cesium/Widgets'), dest: 'cesium' },
      ],
    }),
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium'),
  },
  server: {
    port: 5174,
    strictPort: true,
    host: '127.0.0.1',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
