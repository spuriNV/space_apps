// Captures the main app (frontend/app, port 5170) at 1440x900 into design/screenshots/app/.
// Usage: node design/tools/shoot-app.mjs [name-filter...]   e.g. overview, kings, season, compare   (starts the dev server if needed; start the API on :8000 for live data)
// APP_URL=http://localhost:5171/ to shoot a dev server that is already running elsewhere.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, '..', '..');
const OUT = join(ROOT, 'design', 'screenshots', 'app');
mkdirSync(OUT, { recursive: true });
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const only = process.argv.slice(2);
const FIELD = 'car_colusa_rice';
const T_JUL_2025 = (2025 - 2016) * 36 + 19;

async function up() { try { return (await fetch(BASE)).ok; } catch { return false; } }
let server = null;
if (!(await up())) {
  server = spawn('npm', ['run', 'dev'], { cwd: join(ROOT, 'frontend', 'app'), stdio: 'ignore' });
  for (let i = 0; i < 40 && !(await up()); i++) await new Promise((r) => setTimeout(r, 500));
}
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
page.on('console', (m) => m.type() === 'error' && console.log('console.error', m.text().slice(0, 200)));
page.on('response', (r) => r.status() >= 400 && console.log('HTTP', r.status(), r.url().slice(0, 160)));

const want = (name) => !only.length || only.some((o) => name.includes(o));
async function idle(extra = 900) {
  await page.waitForFunction(() => { const m = window.__map; return m && m.loaded() && !m.isMoving() && m.areTilesLoaded(); }, null, { timeout: 90000, polling: 250 })
    .catch(() => console.log('  (idle wait timed out; shooting anyway)'));
  await page.waitForTimeout(extra);
}
async function shot(name, map = true) { if (map) await idle(); else await page.waitForTimeout(500); await page.screenshot({ path: join(OUT, name) }); console.log('wrote', name); }
async function open() {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="data-indicator"]'), null, { timeout: 90000 });
  await page.evaluate(() => document.fonts.ready);
}
async function pickField(id = FIELD) {
  await page.click(`[data-testid="row-${id}"]`);
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await page.waitForTimeout(1500); // daily weather + outlook
  await idle(600);
}

await open();
if (want('overview')) await shot('overview.png');
await pickField();
if (want('field-now')) await shot('field-now.png');
if (want('coming-season')) { await page.click('[data-testid="tab-season"]'); await page.waitForSelector('[data-testid="coming-season"]'); await shot('coming-season.png', false); await page.click('[data-testid="tab-now"]'); }
if (want('year')) { await page.click('[data-testid="tab-year"]'); await page.waitForSelector('[data-testid="year-sheet"]'); await page.click('[data-testid="ml-on"]').catch(() => console.log('  (no ML calendar)')); await shot('year.png'); await page.click('[data-testid="year-toggle"]'); }
if (want('compare') || want('brief')) {
  await page.click('[data-testid="tab-compare"]');
  await page.waitForSelector('[data-testid="compare"]');
  if (want('compare')) await shot('compare.png', false);
  if (want('brief')) { await page.click('[data-testid="to-brief"]'); await page.waitForSelector('[data-testid="brief"]'); await shot('brief.png', false); await page.click('.br-head .sq-btn'); }
  await page.click('[data-testid="tab-now"]');
}
if (want('drilldown')) {
  await page.evaluate((t) => window.__app.setT(t), T_JUL_2025);
  await page.click('[data-testid="step-drill"]');
  await idle(1500);
  await shot('drilldown-3d.png');
}
if (want('field-now-kings') || want('kings')) {
  await page.evaluate(() => window.__app.setT((2026 - 2016) * 36 + 31));
  await page.click('[data-testid="field-switch"]');
  await page.click('[data-testid="switch-caf_tulare_forage"]');
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await page.waitForTimeout(1500);
  await shot('field-now-kings.png');
}
await browser.close();
if (server) server.kill();
