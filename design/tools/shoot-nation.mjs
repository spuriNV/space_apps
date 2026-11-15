// Screenshot of the Nation tools section: APP_URL=http://localhost:5170/ node design/tools/shoot-nation.mjs [field-id]
// Also prints whether a 390px phone page scrolls sideways with the tools open.
import { chromium } from 'playwright-core';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const id = process.argv[2] ?? 'car_colusa_rice';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
async function run(w, h, out) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  page.on('response', (r) => r.status() >= 400 && console.log('HTTP', r.status(), r.url().slice(0, 140)));
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.click(`[data-testid="row-${id}"]`, { timeout: 90000 });
  await page.waitForSelector('[data-testid="nation-tools"]', { timeout: 90000 });
  await page.waitForSelector('[data-testid="nation-toggle"]', { timeout: 20000 }).catch(async () => { console.log((await page.locator('[data-testid="nation-tools"]').innerText())); process.exit(1); });
  await page.click('[data-testid="nation-toggle"]');
  await page.waitForSelector('[data-testid="nt-funding"] .nt-prog', { timeout: 90000 });
  await page.waitForTimeout(1500);
  if (out) { await page.evaluate(() => document.querySelector('[data-testid="nation-tools"]').scrollIntoView({ block: 'start' })); await page.waitForTimeout(600); await page.screenshot({ path: join(ROOT, 'design', 'screenshots', 'app', out) }); }
  const over = await page.evaluate(() => { const s = document.querySelector('[data-testid="nation-tools"]'); return [document.documentElement.scrollWidth, window.innerWidth, s.scrollWidth, s.clientWidth]; });
  console.log(w, 'scrollWidth/innerWidth/section', over.join(' '));
  await page.close();
}
await run(1100, 2200, 'nation-tools.png');
await run(390, 844, null);
await browser.close();
