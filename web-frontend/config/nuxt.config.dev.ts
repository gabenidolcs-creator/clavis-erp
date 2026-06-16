import { defineNuxtConfig } from 'nuxt/config'
import baseConfig from './nuxt.config.base.ts'

export default defineNuxtConfig({
  ...baseConfig,
  modules: [...(baseConfig.modules || []), '@nuxt/eslint'],
  devtools: { enabled: true },
  // Dev-only SPA mode. The authenticated app shell (Teleport-heavy layout) hits
  // a Vue 3.5 SSR↔client hydration mismatch ("rendered on server: node,
  // expected on client: Symbol(v-cmt)") that escalates to a fatal
  // "Cannot read properties of null (reading 'ce')" — but ONLY once a real auth
  // cookie is present (so it reproduces through the baserow.tinsu.ai domain,
  // never on the cookieless localhost origin). Disabling SSR removes the
  // hydration step entirely, eliminating the crash class for domain dev. Prod
  // keeps SSR (nuxt.config.prod.ts) — the latent hydration bug there is tracked
  // separately.
  ssr: false,
  // When serving dev through the Cloudflare domain, the Vite HMR client must
  // connect back over wss://baserow.tinsu.ai:443. Without this it tries the
  // dev-server origin (localhost:3000), the WS never reaches the browser, and
  // Vite's "deps re-optimized → full reload" signal is lost — leaving the page
  // with two optimizeDeps generations (two Vue copies) and the resulting
  // "Cannot read properties of null (reading 'ce')" hydration crash.
  vite: {
    ...baseConfig.vite,
    server: {
      ...((baseConfig.vite as any)?.server ?? {}),
      allowedHosts: ['baserow.tinsu.ai', 'localhost', '127.0.0.1'],
      // Vite dev serves /_nuxt/...?v=<browserHash> modules with
      // `Cache-Control: immutable, max-age=31536000`. Through the browser HTTP
      // cache (and Cloudflare), chunks from a PRIOR optimizeDeps generation stay
      // cached and keep importing runtime-core?v=<oldHash>, while freshly
      // transformed chunks import ?v=<newHash>. The browser keys ES modules by
      // URL, so the two URLs load Vue TWICE — and a vnode created by one Vue
      // copy, finalized by the other, throws "Cannot read properties of null
      // (reading 'ce')". Forcing no-store on every dev response stops anything
      // from caching stale-hash modules, so only the current generation loads.
      headers: { 'Cache-Control': 'no-store' },
      hmr: {
        protocol: 'wss',
        host: 'baserow.tinsu.ai',
        clientPort: 443,
      },
    },
    optimizeDeps: {
      ...((baseConfig.vite as any)?.optimizeDeps ?? {}),
      // Pre-bundle deps Vite would otherwise discover LAZILY on the first
      // authenticated render. A lazy discovery triggers a mid-session
      // re-optimize that rolls the shared browserHash, so chunks transformed
      // before vs after import runtime-core at two different ?v=<hash> URLs →
      // two Vue copies → "Cannot read properties of null (reading 'ce')".
      // Listing them forces one up-front optimize pass with a single stable hash.
      include: [
        ...(((baseConfig.vite as any)?.optimizeDeps?.include) ?? []),
        '@sentry/core',
      ],
    },
  },
  nitro: {
    devProxy: {
      '/api': { target: 'http://localhost:8000/api', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000/ws', changeOrigin: true, ws: true },
      '/media': { target: 'http://localhost:8000/media', changeOrigin: true },
    },
  },
  hooks: {
    // Prevent Nitro's devStorage from watching the entire repo root with
    // chokidar, which causes EMFILE on macOS in large monorepos / worktrees.
    // See https://github.com/nuxt/nuxt/issues/30481
    'nitro:config'(nitroConfig) {
      nitroConfig.devStorage ??= {}
      nitroConfig.devStorage['root'] = {
        driver: 'fs-lite',
        readOnly: true,
        base: nitroConfig.rootDir,
      }
    },
  },
})
