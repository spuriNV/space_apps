// Captures the "Salmon and the field" section of the BC field panel into design/screenshots/app/bc-salmon.png (desktop panel,
// tall viewport so the whole section shows) and bc-salmon-phone.png. Needs an API that serves /salmon for bc_salmon_river_forage.
// Usage: APP_URL=http://localhost:5171/ node design/tools/shoot-salmon.mjs   (APP_URL defaults to the dev server on :5170)
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.OUT_DIR ?? join(here, '..', 'screenshots', 'app');
mkdirSync(OUT, { recursive: true });
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });

async function openBC(page) {
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  page.on('response', (r) => r.status() >= 400 && console.log('HTTP', r.status(), r.url().slice(0, 140)));
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="topbar"]', { timeout: 90000 });
  await page.waitForTimeout(1500);
  const phone = (page.viewportSize()?.width ?? 1440) <= 640;
  if (phone) {
    await page.click('[data-testid="row-bc_salmon_river_forage"]').catch(async () => { await page.click('[data-testid="field-switch"]'); await page.click('[data-testid="switch-bc_salmon_river_forage"]'); });
  } else {
    await page.click('[data-testid="field-switch"]');
    await page.click('[data-testid="switch-bc_salmon_river_forage"]');
  }
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 30000 });
  await page.waitForSelector('[data-testid="salmon"]', { timeout: 30000 });
  await page.waitForTimeout(800);
}

// desktop: the whole panel, with the charts open
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 2600 } });
  await openBC(page);
  await page.click('[data-testid="salmon-more"]');
  await page.waitForTimeout(900);
  await page.evaluate(() => document.querySelector('[data-testid="salmon"]')?.scrollIntoView({ block: 'start' }));
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(OUT, 'bc-salmon.png') });
  console.log('wrote bc-salmon.png');
  // 2023 view of the flow chart
  await page.click('[data-testid="salmon-year"] button:has-text("2023")');
  await page.waitForTimeout(400);
  await page.locator('[data-testid="salmon-flow"]').screenshot({ path: join(OUT, 'bc-salmon-2023.png') });
  if (process.env.BLOCKS) for (const id of ['temp', 'timing', 'water', 'warning']) await page.locator(`[data-testid="salmon-${id}"]`).screenshot({ path: join(OUT, `bc-salmon-${id}.png`) });
  await page.close();
}
// phone
if (process.argv.includes('phone')) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await openBC(page);
  await page.evaluate(() => { const s = document.querySelector('[data-testid="salmon-more"]'); s?.click(); });
  await page.waitForTimeout(900);
  await page.evaluate(() => document.querySelector('[data-testid="salmon"]')?.scrollIntoView({ block: 'start' }));
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(OUT, 'bc-salmon-phone.png') });
  console.log('wrote bc-salmon-phone.png');
  if (process.env.BLOCKS) for (const id of ['flow', 'timing', 'water']) await page.locator(`[data-testid="salmon-${id}"]`).screenshot({ path: join(OUT, `bc-salmon-phone-${id}.png`) });
}
await browser.close();
