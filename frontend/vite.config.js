import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    include: ['src/**/*.test.{js,jsx,ts,tsx}'],
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
