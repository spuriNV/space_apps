// Captures the main app (frontend/app, port 5170) at 1440x900 into design/screenshots/app/.
// Usage: node design/tools/shoot-app.mjs [name-filter...]   e.g. overview, kings, season, compare, bc   (starts the dev server if needed; start the API on :8000 for live data)
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
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="topbar"]') && document.querySelector('[data-testid="fields-panel"]'), null, { timeout: 90000 });
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
if (want('year')) { await page.click('[data-testid="tab-year"]'); await page.waitForSelector('[data-testid="year-sheet"]'); await page.click('[data-testid="ml-on"]').catch(() => console.log('  (no ML calendar)')); await shot('year.png'); await page.click('[data-testid="year-close"]'); }
if (want('compare') || want('brief')) {
  await page.click('[data-testid="tab-compare"]');
  await page.waitForSelector('[data-testid="compare"]');
  if (want('compare')) await shot('compare.png', false);
  if (want('brief')) { await page.click('[data-testid="to-brief"]'); await page.waitForSelector('[data-testid="brief"]'); await shot('brief.png', false); await page.click('.br-head .sq-btn'); }
  await page.click('[data-testid="tab-now"]');
}
if (want('drilldown')) {
  await page.evaluate((t) => window.__app.setT(t), T_JUL_2025);
  await page.click('[data-testid="field-panel"] [data-testid="more-detail"]'); // the 3D view sits under More detail
  await page.click('[data-testid="step-drill"]');
  await idle(1500);
  await shot('drilldown-3d.png');
  await page.click('[data-testid="field-panel"] [data-testid="more-detail"]');
}
if (want('field-now-kings') || want('kings')) {
  await page.evaluate(() => window.__app.setT((2026 - 2016) * 36 + 31));
  await page.click('[data-testid="field-switch"]');
  await page.click('[data-testid="switch-caf_tulare_forage"]');
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await page.waitForTimeout(1500);
  await shot('field-now-kings.png');
  await page.evaluate(() => document.querySelector('[data-testid="soil-answer"]')?.scrollIntoView({ block: 'center' }));
  await shot('field-now-kings-soil.png', false);
}
// British Columbia (needs an API that serves bc_salmon_river_forage): Field now, the First Nations card under More detail,
// and the reserve outlines map layer (context only)
if ((want('bc') || !only.length) && (await page.evaluate(() => window.__app && document.querySelector('[data-testid="field-switch"]')))) {
  await page.evaluate(() => window.__app.setT((2026 - 2016) * 36 + 31));
  await page.click('[data-testid="field-switch"]');
  const has = await page.$('[data-testid="switch-bc_salmon_river_forage"]');
  if (!has) { console.log('  (no BC field from this API; skipping bc shots)'); await page.keyboard.press('Escape'); }
  else {
    await has.click();
    await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
    await page.waitForTimeout(2500);
    if (want('bc-field-now') || !only.length || only.includes('bc')) await shot('bc-field-now.png');
    if (want('bc-first-nations') || !only.length || only.includes('bc')) {
      await page.click('[data-testid="field-panel"] [data-testid="more-detail"]');
      await page.waitForSelector('[data-testid="first-nations-detail"] h3', { timeout: 20000 }).catch(() => console.log('  (First Nations detail did not load)'));
      await page.evaluate(() => document.querySelector('[data-testid="first-nations"]')?.scrollIntoView({ block: 'start' }));
      await shot('bc-first-nations.png', false);
      await page.click('[data-testid="field-panel"] [data-testid="more-detail"]');
    }
    if (want('bc-map-reserves') || !only.length || only.includes('bc')) {
      await page.click('[data-testid="layers-btn"]');
      await page.click('[data-testid="layer-reserves"]', { force: true });
      await page.waitForTimeout(400);
      await shot('bc-map-reserves-drawer.png', false);
      await page.click('[data-testid="layers-btn"]');
      await page.waitForSelector('[data-testid="reserves-legend"]', { timeout: 20000 });
      await page.evaluate(() => window.__map.easeTo({ zoom: 10.1, duration: 0 }));
      await shot('bc-map-reserves.png');
    }
  }
}
if (want('phone')) {
  const ph = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  ph.on('pageerror', (e) => console.log('PAGE ERROR (phone)', e.message));
  await ph.goto(BASE, { waitUntil: 'domcontentloaded' });
  await ph.waitForSelector(`[data-testid="row-${FIELD}"]`, { timeout: 90000 });
  await ph.evaluate(() => document.fonts.ready);
  await ph.waitForTimeout(1500);
  await ph.screenshot({ path: join(OUT, 'phone-overview.png') }); console.log('wrote phone-overview.png');
  await ph.click(`[data-testid="row-${FIELD}"]`);
  await ph.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await ph.waitForTimeout(4000);
  console.log('phone overflow-x', await ph.evaluate(() => document.documentElement.scrollWidth > window.innerWidth));
  await ph.screenshot({ path: join(OUT, 'phone-field-now.png') }); console.log('wrote phone-field-now.png');
  await ph.click('[data-testid="mtab-compare"]'); await ph.waitForSelector('[data-testid="compare"]'); await ph.waitForTimeout(800);
  await ph.screenshot({ path: join(OUT, 'phone-compare.png') }); console.log('wrote phone-compare.png');
  await ph.close();
}
await browser.close();
if (server) server.kill();
