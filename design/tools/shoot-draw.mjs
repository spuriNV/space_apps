// Draw a field (My fields): drives the real drawing tool on the map, names and saves a field, shoots the panel.
// Usage: APP_URL=http://localhost:5191/ node design/tools/shoot-draw.mjs [draw|panel|phone]   (needs the API: VITE_API_BASE=http://localhost:8003/api)
// Writes design/screenshots/app/draw-field.png (mid-draw), my-field.png (panel) and phone-draw.png (390 px), plus a few extra steps.
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const here = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.OUT_DIR ?? join(here, '..', 'screenshots', 'app');
mkdirSync(OUT, { recursive: true });
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const only = process.argv.slice(2);
const want = (n) => !only.length || only.includes(n);
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const log = (p) => { p.on('pageerror', (e) => console.log('PAGE ERROR', e.message)); p.on('console', (m) => m.type() === 'error' && console.log('console.error', m.text().slice(0, 200))); p.on('response', (r) => r.status() >= 400 && console.log('HTTP', r.status(), r.url().slice(0, 140))); };
async function idle(page, extra = 700) {
  await page.waitForFunction(() => { const m = window.__map; return m && m.loaded() && !m.isMoving() && m.areTilesLoaded(); }, null, { timeout: 60000, polling: 250 }).catch(() => console.log('  (idle timed out)'));
  await page.waitForTimeout(extra);
}
async function open(page) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="draw-btn"], [data-testid="draw-from-list"]'), null, { timeout: 90000 });
  await page.evaluate(() => document.fonts.ready);
  // a farm field near Hanford, close in
  await page.evaluate(() => window.__map.jumpTo({ center: [-119.7975, 36.352], zoom: 15.2, pitch: 0, bearing: 0 }));
  await idle(page, 500);
}
const pt = async (page, lon, lat) => page.evaluate(([x, y]) => { const p = window.__map.project([x, y]); const r = window.__map.getCanvas().getBoundingClientRect(); return { x: r.left + p.x, y: r.top + p.y }; }, [lon, lat]);
const SHAPE = [[-119.8, 36.3505], [-119.7952, 36.3503], [-119.7948, 36.3537], [-119.7985, 36.3541]];

async function tapAt(page, touch, p) { if (touch) await page.touchscreen.tap(p.x, p.y); else await page.mouse.click(p.x, p.y); await page.waitForTimeout(150); }
async function drawShape(page, touch, pts, finish = true) {
  for (const [lon, lat] of pts) await tapAt(page, touch, await pt(page, lon, lat));
  if (finish) await tapAt(page, touch, await pt(page, pts[0][0], pts[0][1]));
}

if (want('draw') || want('panel')) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  log(page);
  await open(page);
  await page.click('[data-testid="draw-btn"]');
  await page.waitForSelector('[data-testid="draw-bar"]');
  await page.waitForTimeout(800);
  await page.click('[data-testid="draw-shape"]');
  await page.waitForTimeout(300);
  await drawShape(page, false, SHAPE, false);
  const c = await pt(page, -119.7992, 36.3515);
  await page.mouse.move(c.x, c.y);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(OUT, 'draw-field.png') });
  console.log('wrote draw-field.png; acres:', await page.textContent('[data-testid="draw-acres"]').catch(() => '(none)'));
  if (want('panel')) {
    await tapAt(page, false, await pt(page, SHAPE[0][0], SHAPE[0][1])); // tap the first point: finish
    await page.waitForSelector('[data-testid="draw-next"]', { timeout: 5000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: join(OUT, 'draw-handles.png') });
    await page.click('[data-testid="draw-next"]');
    await page.waitForSelector('[data-testid="name-dialog"]');
    await page.waitForTimeout(500);
    await page.fill('[data-testid="name-input"]', 'North quarter');
    await page.screenshot({ path: join(OUT, 'draw-name.png') });
    await page.click('[data-testid="name-save"]');
    await page.waitForSelector('[data-testid="field-panel"]');
    await page.waitForTimeout(250);
    await page.screenshot({ path: join(OUT, 'my-field-loading.png') });
    await page.waitForSelector('[data-testid="mine-spans"], [data-testid="mine-error"]', { timeout: 60000 });
    await page.waitForFunction(() => window.__app?.ready, null, { timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(2500);
    await idle(page, 800);
    await page.screenshot({ path: join(OUT, 'my-field.png') });
    console.log('wrote my-field.png; stored:', (await page.evaluate(() => localStorage.getItem('myFields')) ?? '').slice(0, 120));
    await page.click('[data-testid="mine-menu-btn"]');
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(OUT, 'my-field-menu.png') });
  }
  await page.close();
}
if (want('phone')) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  log(page);
  await open(page);
  await page.tap('[data-testid="draw-from-list"]'); // on a phone the pick list is a full page; its "Draw a field" button starts the tool
  await page.waitForSelector('[data-testid="draw-bar"]');
  await page.waitForTimeout(800);
  const small = [[-119.7993, 36.3512], [-119.7957, 36.3511], [-119.7955, 36.3536], [-119.7988, 36.3538]];
  await drawShape(page, true, small, false);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(OUT, 'phone-draw.png') });
  console.log('wrote phone-draw.png');
  await ctx.close();
}
await browser.close();
