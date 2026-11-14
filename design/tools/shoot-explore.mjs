// Captures the six exploration screens (design/explorations, dev server on :5180).
// Usage: node shoot-explore.mjs [only-prefix]   e.g. node shoot-explore.mjs year-2
import { chromium } from 'playwright-core';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'screenshots', 'explore');
const BASE = process.env.X_URL ?? 'http://localhost:5180/';
const only = process.argv[2];
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('console.error:', m.text().slice(0, 200)); });

const shots = [
  ['year-1.png', '?screen=year&opt=1&year=2023'],
  ['year-2.png', '?screen=year&opt=2&year=2022'],
  ['year-3.png', '?screen=year&opt=3&year=2022'],
  ['compare-1.png', '?screen=compare&opt=1'],
  ['compare-2.png', '?screen=compare&opt=2&alt=car2_dryyear_safflower'],
  ['compare-3.png', '?screen=compare&opt=3&a=car1_rice_wintercover&b=car2_dryyear_safflower'],
];
for (const [name, qs] of shots) {
  if (only && !name.startsWith(only)) continue;
  await page.goto(BASE + qs, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(OUT, name) });
  console.log('saved', name);
}
await browser.close();
