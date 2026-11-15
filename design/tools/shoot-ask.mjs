// Ask CropLytics popover (components/chat/AskChat.tsx): desktop and phone shots, plus an accessibility pass
// (focus lands in the box on open, Escape returns focus to Ask, one live announcement per answer).
// Usage: APP_URL=http://localhost:8000/ node design/tools/shoot-ask.mjs   (API on :8000 serving the built frontend, chat key set)
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.OUT_DIR ?? join(here, '..', 'screenshots', 'app');
mkdirSync(OUT, { recursive: true });
const BASE = process.env.APP_URL ?? 'http://localhost:8000/';
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });

async function run(name, viewport) {
  const page = await browser.newPage({ viewport });
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__app, null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.__app.select('caf_tulare_forage'));
  await page.waitForFunction(() => window.__app.ready, null, { timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.click('[data-testid=ask-btn]');
  const focused = await page.evaluate(() => document.activeElement?.id);
  console.log(name, 'focus after open:', focused);
  await page.screenshot({ path: join(OUT, `ask-${name}-open.png`) });
  await page.fill('#ask-q', 'Is my groundwater okay?');
  await page.keyboard.press('Enter');
  await page.waitForSelector('.ask-msg.assistant:not(.ask-busy)', { timeout: 40000 });
  const live = await page.textContent('.ask-pop [aria-live=polite]');
  console.log(name, 'announced:', live);
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(OUT, `ask-${name}-answer.png`) });
  await page.keyboard.press('Escape');
  console.log(name, 'focus after Escape:', await page.evaluate(() => document.activeElement?.getAttribute('data-testid')));
  await page.close();
}
await run('desktop', { width: 1440, height: 900 });
await run('phone', { width: 390, height: 844 });
await browser.close();
