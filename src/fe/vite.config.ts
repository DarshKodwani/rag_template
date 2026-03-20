/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const repoRoot = path.resolve(__dirname, '..', '..')

/**
 * Redirects bare module imports from test files in tests/fe/
 * so they resolve via src/fe/node_modules instead.
 */
function resolveTestDeps(): Plugin {
  const testsDir = path.resolve(repoRoot, 'tests', 'fe')
  const fakeImporter = path.resolve(__dirname, 'src', '_resolve_anchor_.ts')
  return {
    name: 'resolve-test-deps',
    enforce: 'pre',
    async resolveId(source, importer) {
      if (!importer || !importer.startsWith(testsDir)) return
      if (source.startsWith('.') || source.startsWith('/') || source.startsWith('@/')) return
      const resolved = await this.resolve(source, fakeImporter, { skipSelf: true })
      return resolved
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), resolveTestDeps()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: path.resolve(repoRoot, 'tests', 'fe', 'setup.ts'),
    include: [path.resolve(repoRoot, 'tests', 'fe', '**', '*.test.{ts,tsx}')],
    exclude: [path.resolve(repoRoot, 'tests', 'fe', 'node_modules', '**')],
    css: true,
  },
})
