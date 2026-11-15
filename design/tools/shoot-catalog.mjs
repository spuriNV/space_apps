// Farm catalog pins and list: APP_URL=http://localhost:5170/ node design/tools/shoot-catalog.mjs
import { chromium } from 'playwright-core';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const BASE = process.env.APP_URL ?? 'http://localhost:5170/';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="farm-catalog"]', { timeout: 90000 });
await page.click('[data-testid="farm-catalog"] .cg-toggle');
await page.waitForTimeout(2500);
await page.screenshot({ path: join(ROOT, 'design', 'screenshots', 'app', 'farm-catalog.png') });
await page.click('[data-testid="farm-catalog"] .cg-row');
await page.waitForSelector('[data-testid="spot-label"]', { timeout: 60000 });
console.log('spot opened', await page.evaluate(() => location.hash));
await browser.close();
