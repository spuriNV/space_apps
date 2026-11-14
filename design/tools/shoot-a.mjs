// Screenshots for design variant A ("Maps classic"). Needs the dev server on :5171
//   cd frontend/variants/a-maps && npm run dev
//   cd design/tools && node shoot-a.mjs            (six required states)
//   node shoot-a.mjs --extras <dir>                (also saves extra states to <dir> for review)
import { chromium } from 'playwright-core';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, '..', 'screenshots');
const extrasAt = process.argv.indexOf('--extras');
const EXTRAS = extrasAt > 0 ? process.argv[extrasAt + 1] : null;
const URL = 'http://127.0.0.1:5171/';

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('console error:', m.text().slice(0, 200)); });

/** wait until the camera is still and every tile in view has loaded */
async function idle(extra = 600) {
  await page.waitForFunction(() => {
    const m = window.__map;
    return m && m.loaded() && m.areTilesLoaded() && !m.isMoving();
  }, null, { timeout: 45000, polling: 250 }).catch(() => console.log('  (idle wait timed out, shooting anyway)'));
  await page.waitForFunction(() => [...document.images].every((i) => i.complete), null, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(extra);
}
async function shot(name, dir = OUT) {
  await idle();
  await page.screenshot({ path: join(dir, name) });
  console.log('saved', name);
}
/** screen position of a lon/lat (the map canvas is offset by the place panel) */
async function screenOf(lon, lat) {
  return page.evaluate(([lo, la]) => {
    const m = window.__map, p = m.project([lo, la]), r = m.getContainer().getBoundingClientRect();
    return { x: r.left + p.x, y: r.top + p.y };
  }, [lon, lat]);
}

await page.goto(URL, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__map && window.__map.loaded(), null, { timeout: 60000 });
await page.evaluate(() => document.fonts.ready);

// 01 California overview: both preset pins, search pill, chips
await shot('a-01-overview.png');

if (EXTRAS) {
  await page.click('.search input');
  await page.waitForTimeout(300);
  await shot('x-search.png', EXTRAS);
  await page.keyboard.press('Escape');
  await page.click('.chip:has-text("Soil moisture")');
  await page.evaluate(() => window.__map.flyTo({ center: [-121.2, 37.8], zoom: 7.2, duration: 0 }));
  await shot('x-soil.png', EXTRAS);
  await page.click('.chip:has-text("Soil moisture")');
  await page.evaluate(() => window.__map.jumpTo({ center: [-119.6, 37.55], zoom: 5.75 }));
}

// 02 click the Colusa pin: place panel opens, camera flies to the field inside its SMAP pixel
await page.click('.pin-field >> nth=0');
await page.waitForTimeout(2600);
await shot('a-02-field.png');

// 03 scroll in on the field: camera pitches and the 30 m cells rise
const C = [-122.1, 39.15];
let pt = await screenOf(...C);
await page.mouse.move(pt.x, pt.y);
for (let i = 0; i < 14; i++) { await page.mouse.wheel(0, -260); await page.waitForTimeout(140); }
await page.waitForTimeout(900);
await page.evaluate(([lo, la]) => window.__map.easeTo({ center: [lo, la + 0.0006], zoom: 15.2, bearing: -24, duration: 1200 }), C);
await page.waitForTimeout(1500);
await shot('a-03-drilldown-3d.png');

if (EXTRAS) {
  await page.click('.measure-grid button:has-text("Stress")');
  await shot('x-stress.png', EXTRAS);
  await page.click('.layers');
  await shot('x-satellite-3d.png', EXTRAS);
  await page.click('.layers');
  await page.click('.measure-grid button:has-text("Cover")');
}

// 06 design idea: replay a year on the 3D field with a time scrubber
await page.click('.legend-foot .pill-btn');
await page.waitForTimeout(400);
const track = await page.locator('.replay-track input').boundingBox();
await page.mouse.click(track.x + 8 + ((track.width - 16) * 23.5) / 51, track.y + 30); // mid-June 2023
await page.waitForTimeout(500);
await page.mouse.move(pt.x + 200, 300);
await shot('a-06-idea.png');
await page.click('.replay .icon-btn[aria-label="Close replay"]');

// 04 Your field's year
await page.click('.action:has-text("Field\'s year")');
await page.waitForTimeout(500);
await page.click('.news-pin >> nth=0');
await page.waitForTimeout(600);
await shot('a-04-year.png');

// 05 Compare rotations
await page.click('.tab:has-text("Compare")');
await page.waitForTimeout(600);
await shot('a-05-compare.png');

if (EXTRAS) {
  await page.click('.seg button:has-text("Replay 2022")');
  await shot('x-compare-2022.png', EXTRAS);
  await page.click('.tabs-right .pill-btn:has-text("Brief")');
  await shot('x-brief.png', EXTRAS);
  await page.keyboard.press('Escape');
  await page.click('.tab:has-text("Sources")');
  await shot('x-sources.png', EXTRAS);
  await page.click('.search input');
  await page.click('.suggest-row:has-text("Why not BC yet")');
  await page.waitForTimeout(2500);
  await shot('x-bc.png', EXTRAS);
  await page.click('.search input');
  await page.click('.suggest-row:has-text("Tulare")');
  await page.waitForTimeout(3000);
  await shot('x-tulare.png', EXTRAS);
  await page.click('.drill-card');
  await page.waitForTimeout(3200);
  await shot('x-tulare-3d.png', EXTRAS);
}

await browser.close();
