// Screenshot of the "This week" card: APP_URL=http://localhost:5170/ node design/tools/shoot-week.mjs [field-id]
// Also prints whether a 390px phone page scrolls sideways.
import { chromium } from 'playwright-core';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const id = process.argv[2] ?? 'caf_tulare_forage';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
async function run(w, h, out) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.click(`[data-testid="row-${id}"]`, { timeout: 90000 });
  await page.waitForSelector('[data-testid="tw-access"]', { timeout: 90000 });
  await page.waitForTimeout(1500);
  if (out) {
    await page.click('[data-testid="tw-access"] .tw-chip.too_wet, [data-testid="tw-access"] .tw-chip:nth-child(3)');
    await page.evaluate(() => document.querySelector('[data-testid="this-week"]').scrollIntoView({ block: 'start' }));
    await page.waitForTimeout(600);
    await page.screenshot({ path: join(ROOT, 'design', 'screenshots', 'app', out) });
  }
  console.log(w, 'overflow', await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth, document.querySelector('[data-testid="this-week"]').scrollWidth, document.querySelector('[data-testid="this-week"]').clientWidth].join(' ')));
  await page.close();
}
await run(1100, 1000, 'this-week.png');
await run(390, 844, null);
await browser.close();
