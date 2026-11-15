// SPDX-License-Identifier: Apache-2.0
/// <reference types='vitest' />
import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { nxReadySignal } from '@nx/vite/plugins/nx-ready-signal.plugin';

const workspaceRoot = path.resolve(import.meta.dirname, '../..');

export default defineConfig(() => ({
  root: import.meta.dirname,
  cacheDir: '../../node_modules/.vite/apps/dashboard',
  server: {
    port: 4200,
    host: 'localhost',
    fs: {
      // src/findings.ts bundles findings/*/*.json from the workspace root with
      // import.meta.glob. Serve only the app, the findings and the installed packages.
      strict: true,
      allow: [
        import.meta.dirname,
        path.join(workspaceRoot, 'findings'),
        path.join(workspaceRoot, 'node_modules'),
      ],
    },
  },
  preview: {
    port: 4300,
    host: 'localhost',
  },
  resolve: {
    tsconfigPaths: true,
  },
  plugins: [react(), nxReadySignal()],
  // Uncomment this if you are using workers.
  // worker: {
  //  plugins: [],
  // },
  build: {
    outDir: '../../dist/apps/dashboard',
    emptyOutDir: true,
    // The build is a single chunk, so the modulepreload polyfill (which fetches preload links)
    // has nothing to do; leaving it out keeps fetch() out of the bundle.
    modulePreload: { polyfill: false },
    reportCompressedSize: true,
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
  define: {
    'import.meta.vitest': undefined,
  },
  test: {
    name: 'dashboard',
    watch: false,
    // The cached transform of src/findings.ts keeps its import.meta.glob matches, so a
    // finding added after the first run would be missing from the tests.
    fsModuleCache: false,
    globals: true,
    environment: 'jsdom',
    include: ['{src,tests}/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    includeSource: ['src/**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    reporters: ['default'],
    coverage: {
      reportsDirectory: '../../coverage/apps/dashboard',
      provider: 'v8' as const,
    },
  },
}));
