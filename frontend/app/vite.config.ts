import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { readFile } from 'node:fs/promises';
import { join, normalize, resolve } from 'node:path';

// Dev-only bridge: serves real backend outputs that the API has no route for yet (see README "API routes still needed").
// Read-only, allow-listed paths under the repo root. Remove once backend/api serves these.
const ROOT = resolve(__dirname, '..', '..');
const ALLOW = [/^backend\/field\/polygons\/[a-z_]+\.geojson$/, /^backend\/field\/out\/[a-z_]+\/(calendar|crop_history)\.json$/, /^backend\/field\/out\/[a-z_]+\/grid\.geojson$/, /^data\/cache\/[a-z_]+\/soil\.json$/, /^backend\/news\/out\/[a-z_]+\.json$/];
function repoBridge(): Plugin {
  return {
    name: 'repo-bridge',
    configureServer(server) {
      server.middlewares.use('/repo/', async (req, res) => {
        const rel = normalize(decodeURIComponent((req.url ?? '').split('?')[0].replace(/^\/+/, '')));
        if (!ALLOW.some((r) => r.test(rel))) { res.statusCode = 404; res.end('not allowed'); return; }
        try {
          const body = await readFile(join(ROOT, rel));
          res.setHeader('content-type', 'application/json');
          res.end(body);
        } catch { res.statusCode = 404; res.end('missing'); }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), repoBridge()],
  server: { port: 5170, strictPort: true },
  preview: { port: 5170, strictPort: true },
});
