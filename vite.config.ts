import { defineConfig } from 'vite'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      '@core': resolve(__dirname, 'src/core'),
      '@adapters': resolve(__dirname, 'src/adapters'),
    },
  },
  optimizeDeps: {
    exclude: ['@babylonjs/havok'],
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
})
