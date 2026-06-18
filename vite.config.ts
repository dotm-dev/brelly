import { defineConfig } from 'vite'
import { resolve } from 'path'

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
