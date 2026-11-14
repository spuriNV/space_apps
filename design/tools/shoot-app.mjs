// Captures the main app (frontend/app, port 5170) at 1440x900 into design/screenshots/app/.
// Usage: node design/tools/shoot-app.mjs [name-filter...]   e.g. theme2, drilldown, brief   (starts the dev server if needed; start the API on :8000 for live data)
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, '..', '..');
const OUT = join(ROOT, 'design', 'screenshots', 'app');
mkdirSync(OUT, { recursive: true });
const BASE = 'http://localhost:5170/';
const only = process.argv.slice(2);
const FIELD = 'caf_tulare_forage';
const T_JUL_2023 = (2023 - 2016) * 36 + 19;

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

const want = (name) => !only.length || only.some((o) => name.includes(o));
async function idle(extra = 900) {
  await page.waitForFunction(() => { const m = window.__map; return m && m.loaded() && !m.isMoving() && m.areTilesLoaded(); }, null, { timeout: 90000, polling: 250 })
    .catch(() => console.log('  (idle wait timed out; shooting anyway)'));
  await page.waitForTimeout(extra);
}
async function shot(name) { await idle(); await page.screenshot({ path: join(OUT, name) }); console.log('wrote', name); }
async function open(theme) {
  await page.goto(`${BASE}?theme=${theme}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="data-indicator"]'), null, { timeout: 90000 });
}
async function pickField() {
  await page.click(`[data-testid="row-${FIELD}"]`);
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await page.evaluate((t) => window.__app.setT(t), T_JUL_2023);
  await idle(600);
}

// ?theme=1|2|3: survey sheet (default), extension bulletin, field desk. Same farmer-first panel in each.
for (const th of [1, 2, 3]) {
  if (!want(`theme${th}`)) continue;
  await open(th);
  await page.evaluate(() => document.fonts.ready);
  await shot(`theme${th}-overview.png`);
  await pickField();
  await shot(`theme${th}-field.png`);
}
if (want('drilldown') || want('brief')) {
  await open(1);
  await pickField();
  if (want('drilldown')) {
    await page.click('[data-testid="step-drill"]');
    await idle(1200);
    await shot('drilldown-3d.png');
  }
  if (want('brief')) {
    await page.click('[data-testid="step-brief"]');
    await page.waitForSelector('[data-testid="brief"]');
    await page.selectOption('[data-testid="brief-pick"]', 'caf3_alfalfa_break');
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(OUT, 'brief.png') });
    console.log('wrote brief.png');
  }
}
await browser.close();
if (server) server.kill();
