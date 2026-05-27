import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Unit/component tests only. The Playwright e2e specs under tests/regression
    // run with their own runner against a live server, not vitest.
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
