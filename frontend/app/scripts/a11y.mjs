// Automated accessibility check: loads Pick and Now for Colusa and fails on serious or critical axe violations.
//   node scripts/a11y.mjs [baseUrl]      (default http://localhost:5171; start `npm run dev -- --port 5171` or `vite preview` first)
// Chromium: Playwright's own, else the newest one under ~/.cache/ms-playwright (or CHROMIUM_PATH).
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import { readdirSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const base = process.argv[2] ?? 'http://localhost:5171';
function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const root = join(homedir(), '.cache', 'ms-playwright');
  if (!existsSync(root)) return undefined;
  const dirs = readdirSync(root).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => parseInt(b.slice(9)) - parseInt(a.slice(9)));
  for (const d of dirs) for (const sub of ['chrome-linux64/chrome', 'chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) { const p = join(root, d, sub); if (existsSync(p)) return p; }
  return undefined;
}
const browser = await chromium.launch({ executablePath: findChromium(), args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let bad = 0;
async function check(name, page) {
  const r = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).exclude('.maplibregl-canvas').analyze();
  const hard = r.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  const soft = r.violations.filter((v) => !hard.includes(v));
  console.log(`${name}: ${hard.length} serious/critical, ${soft.length} minor/moderate`);
  for (const v of hard) console.log(`  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length}) e.g. ${v.nodes[0]?.target?.join(' ')}`);
  for (const v of soft) console.log(`  (${v.impact}) ${v.id} (${v.nodes.length})`);
  bad += hard.length;
}
for (const [label, w, h, outdoor] of [['desktop', 1440, 900, false], ['phone', 390, 844, false], ['desktop outdoor', 1440, 900, true]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  if (outdoor) await page.addInitScript(() => localStorage.setItem('croplytics.a11y', JSON.stringify({ outdoor: true, pause: false })));
  await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('[data-testid=row-car_colusa_rice]', { timeout: 30000 });
  await page.waitForTimeout(1500);
  await check(`${label} / Pick`, page);
  await page.click('[data-testid=row-car_colusa_rice]');
  await page.waitForSelector('[data-testid=step-answer]', { timeout: 30000 });
  await page.waitForTimeout(2500);
  await check(`${label} / Now (Colusa)`, page);
  await ctx.close();
}
await browser.close();
console.log(bad ? `FAIL: ${bad} serious/critical violations` : 'PASS: 0 serious/critical violations');
process.exit(bad ? 1 : 0);
