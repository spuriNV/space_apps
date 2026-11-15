// Screenshots the newest features (This week, Nation tools, draw a field, farm catalog) to plan the v2 shots.
import { chromium } from '../../design/tools/node_modules/playwright-core/index.mjs';
const BASE = process.env.APP_URL ?? 'https://croplytics.xyz/';
const OUT = new URL('../raw/ex2/', import.meta.url).pathname;
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=metal', '--ignore-gpu-blocklist', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
const idle = async (x = 800) => { await page.waitForFunction(() => { const m = window.__map; return m && m.loaded() && !m.isMoving() && m.areTilesLoaded(); }, null, { timeout: 90000, polling: 250 }).catch(() => console.log('idle timeout')); await page.waitForTimeout(x); };
const shot = async (n) => { await page.screenshot({ path: OUT + n + '.png' }); console.log('shot', n); };
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="fields-panel"]'), null, { timeout: 120000 });
await idle(2000); await shot('a-overview');
console.log('panel', (await page.innerText('[data-testid="fields-panel"]')).replace(/\s+/g, ' ').slice(0, 600));
await page.click('[data-testid="row-car_colusa_rice"]');
await page.waitForFunction(() => window.__app?.ready, null, { timeout: 60000 }); await page.waitForTimeout(3000); await idle(1500);
await shot('b-field');
const p = await page.$('[data-testid="field-panel"]');
console.log('panel', (await p.innerText()).replace(/\s+/g, ' ').slice(0, 1500));
console.log('this-week', !!(await page.$('[data-testid="this-week"]')), 'nation', !!(await page.$('[data-testid="nation-tools"]')));
const nt = await page.$('[data-testid="nation-toggle"]');
if (nt) { await nt.scrollIntoViewIfNeeded(); await nt.click(); await page.waitForTimeout(2500); await shot('c-nation'); }
await browser.close();
