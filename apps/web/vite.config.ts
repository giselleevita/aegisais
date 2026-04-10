import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import fs from 'node:fs'
import path from 'node:path'

const CESIUM_BUILD_DIR = path.resolve(__dirname, '../../node_modules/cesium/Build/Cesium')

const MIME: Record<string, string> = {
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.wasm': 'application/wasm',
  '.glb': 'model/gltf-binary',
  '.ktx2': 'image/ktx2',
}

/** Serves Cesium static assets at /cesium/* during `vite dev`. */
function cesiumDevServer() {
  return {
    name: 'vite-cesium-dev-server',
    configureServer(server: import('vite').ViteDevServer) {
      server.middlewares.use('/cesium', (req, res, next) => {
        const filePath = path.join(CESIUM_BUILD_DIR, req.url ?? '')
        try {
          const stat = fs.statSync(filePath)
          if (stat.isFile()) {
            const ext = path.extname(filePath)
            res.setHeader('Content-Type', MIME[ext] ?? 'application/octet-stream')
            fs.createReadStream(filePath).pipe(res)
            return
          }
        } catch {
          // file not found — fall through
        }
        next()
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    cesiumDevServer(),
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
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/cesium/')) {
            return 'vendor-cesium'
          }
          if (id.includes('/node_modules/react/') || id.includes('/node_modules/react-dom/')) {
            return 'vendor-react'
          }
          if (id.includes('/node_modules/react-router-dom/') || id.includes('/node_modules/@remix-run/')) {
            return 'vendor-router'
          }
          if (
            id.includes('/node_modules/leaflet/') ||
            id.includes('/node_modules/react-leaflet/')
          ) {
            return 'vendor-maps'
          }
          return undefined
        },
      },
    },
  },
})
