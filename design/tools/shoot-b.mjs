// Captures the six required states of variant B (Earth explorer) at 1440x900.
// Usage: node design/tools/shoot-b.mjs   (starts the dev server on :5172 if it is not already running)
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, '..', '..');
const OUT = join(ROOT, 'design', 'screenshots');
const URL = 'http://localhost:5172/';
const only = process.argv.slice(2);

async function up() { try { return (await fetch(URL)).ok; } catch { return false; } }
let server = null;
if (!(await up())) {
  server = spawn('npm', ['run', 'dev'], { cwd: join(ROOT, 'frontend', 'variants', 'b-earth'), stdio: 'ignore' });
  for (let i = 0; i < 40 && !(await up()); i++) await new Promise((r) => setTimeout(r, 500));
}

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
page.on('console', (m) => m.type() === 'error' && console.log('console.error', m.text().slice(0, 200)));

async function idle(extra = 900) {
  await page.waitForFunction(() => {
    const m = window.__map;
    return m && m.loaded() && !m.isMoving() && m.areTilesLoaded();
  }, null, { timeout: 90000, polling: 250 }).catch(() => console.log('  (idle wait timed out; shooting anyway)'));
  await page.waitForTimeout(extra);
}
async function shot(name) {
  if (only.length && !only.some((o) => name.includes(o))) return;
  await idle();
  await page.screenshot({ path: join(OUT, name) });
  console.log('wrote', name);
}

await page.goto(URL, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__map && window.__map.loaded(), null, { timeout: 90000 });
await shot('b-01-overview.png');

// 02: click the Colusa marker -> knowledge card + pixel footprints
await page.click('.pin[data-id="car_colusa_rice"]');
await page.waitForSelector('[data-testid="kcard"]');
await idle(600);
await shot('b-02-field.png');

// scroll-driven tilt check (real wheel events over the field)
{
  const c = await page.evaluate(() => { const m = window.__map; const p = m.project([-122.1, 39.15]); return [p.x, p.y]; });
  await page.mouse.move(c[0], c[1]);
  for (let i = 0; i < 14; i++) { await page.mouse.wheel(0, -320); await page.waitForTimeout(140); }
  await idle(300);
  console.log('after wheel:', await page.evaluate(() => ({ zoom: +window.__map.getZoom().toFixed(2), pitch: +window.__map.getPitch().toFixed(1) })));
}

// 03: drill down (button on the card gives a deterministic camera)
await page.click('[data-testid="drill"]');
await idle(600);
await shot('b-03-drilldown-3d.png');

// 04: your field's year (expanded timeline), 2022 fallow selected, ML detector toggled then back to rule
await page.click('[data-testid="year-toggle"]');
await page.waitForSelector('[data-testid="year-sheet"]');
await page.click('.ys-row:nth-child(8) .ys-strip button:nth-child(15)'); // 2022, late May
await page.click('[data-testid="det-ml"]');
await page.click('[data-testid="det-rule"]');
await idle(600);
await shot('b-04-year.png');

// 05: compare
await page.click('[data-testid="rail-compare"]');
await page.waitForSelector('[data-testid="compare"]');
await shot('b-05-compare.png');

// 06: story mode, chapter 3 (January 2023 storms)
await page.click('[data-testid="rail-story"]');
await page.waitForSelector('[data-testid="story"]');
await page.click('[data-testid="chapter-2"]');
await idle(600);
await shot('b-06-idea.png');

await browser.close();
if (server) server.kill();
