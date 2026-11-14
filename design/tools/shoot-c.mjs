// Captures the six variant-C states by driving the real UI.
// Usage: (dev server running on :5173)  node shoot-c.mjs [only-prefix]
import { chromium } from 'playwright-core';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'screenshots');
const URL = process.env.C_URL ?? 'http://localhost:5173/';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('console.error:', m.text().slice(0, 200)); });

/** Wait until the camera is at rest and every visible tile has loaded. */
async function idle(extra = 700) {
  await page.waitForFunction(() => !!window.__map && window.__map.loaded(), null, { timeout: 60000 });
  await page.evaluate(() => new Promise((res) => {
    const m = window.__map;
    const ok = () => m.loaded() && !m.isMoving() && m.areTilesLoaded();
    if (ok()) return res();
    const t = setTimeout(res, 25000);
    const h = () => { if (ok()) { clearTimeout(t); m.off('idle', h); res(); } };
    m.on('idle', h);
  }));
  await page.waitForTimeout(extra);
}
const shot = async (name) => { await page.screenshot({ path: join(OUT, name) }); console.log('saved', name); };

await page.goto(URL, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('.pinpill');
await document_fonts();
async function document_fonts() { await page.evaluate(() => document.fonts.ready); }
await idle(1200);

// 01 overview: hover the first card so the list → map sync is visible
await page.hover('.fcard[data-loc="car_colusa_rice"]');
await idle(400);
await shot('c-01-overview.png');

// 02 open the Colusa field from its card
await page.click('.fcard[data-loc="car_colusa_rice"]');
await page.waitForSelector('.rcard');
await page.mouse.move(700, 870);
await idle(1500);
await shot('c-02-field.png');

// 03 scroll into the field: the map pitches and the 30 m cells extrude
const box = await page.locator('.mapwrap').boundingBox();
const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
await page.mouse.move(cx, cy);
for (let i = 0; i < 14 && !(await page.locator('.inspector').count()); i++) {
  await page.mouse.wheel(0, -400);
  await page.waitForTimeout(450);
}
await page.waitForSelector('.inspector', { timeout: 20000 });
await idle(2500);
await idle(800);
// click a cell for the readout (try a few points until one hits a block)
for (const [dx, dy] of [[40, -60], [0, -30], [-60, -80], [80, -20], [0, -120]]) {
  await page.mouse.click(cx + dx, cy + dy);
  await page.waitForTimeout(300);
  if (await page.locator('.insp-cell dl').count()) break;
}
await page.mouse.move(cx + 200, box.y + 60);
await idle(600);
await shot('c-03-drilldown-3d.png');

// 04 your field's year (leave 3D first)
await page.click('.insp-close');
await page.click('[data-tab="year"]');
await idle(1500);
await shot('c-04-year.png');

// 05 compare
await page.click('[data-tab="compare"]');
await page.waitForSelector('.ctable');
await idle(1500);
await shot('c-05-compare.png');

// 06 printable rotation brief for "Rice + winter cover"
await page.click('[data-brief="car1_rice_wintercover"]');
await page.waitForSelector('.paper');
await page.waitForTimeout(600);
await shot('c-06-idea.png');

await browser.close();
