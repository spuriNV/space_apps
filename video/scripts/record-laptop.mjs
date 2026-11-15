// Records the laptop shots (v2 shots: this week, nation tools, 3D, compare, brief, draw a field; see docs/video-30s.md §0b) from the live app at 1600x900 CSS px (1920x1080 device px)
// with Chrome's screencast (JPEG frames + timestamps), then builds one constant-24-fps MP4 per take in video/raw/rec/.
// Usage: node video/scripts/record-laptop.mjs [take-filter...]   (APP_URL=... to point elsewhere)
import { chromium } from '../../design/tools/node_modules/playwright-core/index.mjs';
import { mkdirSync, writeFileSync, rmSync, symlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const BASE = process.env.APP_URL ?? 'https://croplytics.xyz/';
const OUT = new URL('../raw/rec/', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const only = process.argv.slice(2);
const want = (n) => !only.length || only.some((o) => n.includes(o));

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=metal', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.2 });
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
const cdp = await page.context().newCDPSession(page);
let frames = null;
cdp.on('Page.screencastFrame', async (f) => {
  if (frames) frames.push({ t: f.metadata.timestamp, data: f.data });
  await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
});
let t0 = 0;
async function start() { frames = []; t0 = Date.now() / 1000; await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 }); return Date.now() / 1000; }
async function stop(name) {
  const end = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  const fr = frames; frames = null;
  fr.forEach((f) => { f.t = Math.max(f.t, t0); }); // the first frame can carry an older timestamp
  const dir = `${OUT}${name}_frames/`; rmSync(dir, { recursive: true, force: true }); mkdirSync(dir);
  // one symlink per output frame at 24 fps: the latest captured frame at that moment
  fr.forEach((f, i) => writeFileSync(`${dir}${String(i).padStart(5, '0')}.jpg`, Buffer.from(f.data, 'base64')));
  const seq = `${dir}seq/`; mkdirSync(seq);
  const n = Math.round((end - t0) * 24);
  for (let k = 0, j = 0; k < n; k++) {
    const t = t0 + k / 24;
    while (j + 1 < fr.length && fr[j + 1].t <= t) j++;
    symlinkSync(`${dir}${String(j).padStart(5, '0')}.jpg`, `${seq}${String(k).padStart(5, '0')}.jpg`);
  }
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', '24', '-i', `${seq}%05d.jpg`, '-vf', 'scale=1920:1080:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-crf', '14', '-preset', 'medium', `${OUT}${name}.mp4`]);
  const span = fr.length ? end - fr[0].t : 0;
  console.log(`take ${name}: ${fr.length} frames over ${span.toFixed(1)} s (${(fr.length / Math.max(span, 0.01)).toFixed(1)} fps captured)`);
}
const idle = async (extra = 800) => { await page.waitForFunction(() => { const m = window.__map; return m && m.loaded() && !m.isMoving() && m.areTilesLoaded(); }, null, { timeout: 90000, polling: 250 }).catch(() => console.log('  idle timeout')); await page.waitForTimeout(extra); };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="fields-panel"]'), null, { timeout: 120000 });
await page.evaluate(() => document.fonts.ready); await idle(1500);

// Shot 7 setup: the field open, "Field now"
// the app falls back to bundled example numbers when the API is slow; only record the live data
// (live: rain since 1 Oct is a number, and the field's water need matches /api/.../strategies)
for (let attempt = 1; ; attempt++) {
  await page.click('[data-testid="row-car_colusa_rice"]');
  await page.waitForFunction(() => window.__app?.ready, null, { timeout: 60000 }); await page.waitForTimeout(2500); await idle(1500);
  const txt = (await page.innerText('[data-testid="field-panel"]')).replace(/\s+/g, ' ');
  const live = /Rain since 1 Oct \d+(\.\d)? in/.test(txt) && !/Not available/.test(txt.slice(0, 600));
  console.log(`  field panel (attempt ${attempt}): ${live ? 'live data' : 'NOT live'} :: ${txt.slice(0, 260)}`);
  if (live) break;
  if (attempt >= 4) throw new Error('the app never showed live data');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="fields-panel"]'), null, { timeout: 120000 });
  await idle(1500);
}

const moreDetail = '[data-testid="field-panel"] [data-testid="more-detail"]';
// This week card (top of Field now): irrigation and field access
if (want('s07')) {
  await start();
  await page.waitForTimeout(3600);
  await stop('s07_week');
}

// Nation tools: open the tools, glide down to the drought rotation bars
if (want('s09')) {
  await page.click(moreDetail); await page.waitForTimeout(800);
  await page.locator('[data-testid="nation-toggle"]').scrollIntoViewIfNeeded(); await page.waitForTimeout(600);
  await start();
  await page.waitForTimeout(500);
  await page.click('[data-testid="nation-toggle"]');
  await page.waitForTimeout(1500);
  await page.evaluate(async () => {
    const h = document.querySelector('[data-testid="nt-drought"]');
    let el = h; while (el && !(el.scrollHeight > el.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(el).overflowY))) el = el.parentElement;
    if (!h || !el) return;
    const target = el.scrollTop + h.getBoundingClientRect().top - el.getBoundingClientRect().top - 12;
    const from = el.scrollTop, t0 = performance.now(), dur = 1100;
    await new Promise((res) => { const step = (now) => { const k = Math.min(1, (now - t0) / dur); const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2; el.scrollTop = from + (target - from) * e; k < 1 ? requestAnimationFrame(step) : res(); }; requestAnimationFrame(step); });
  });
  await page.waitForTimeout(2400);
  await stop('s09_nation');
  await page.click('[data-testid="nation-toggle"]').catch(() => {}); await page.waitForTimeout(500);
  await page.click(moreDetail).catch(() => {}); await page.waitForTimeout(500);
}

if (want('s08')) {
  await page.click(moreDetail); await page.waitForTimeout(600);
  await start();
  await page.waitForTimeout(500);
  await page.click('[data-testid="step-drill"]');
  await page.waitForTimeout(3500);
  await page.evaluate(() => { const m = window.__map; m.easeTo({ bearing: m.getBearing() + 22, duration: 4000, easing: (t) => t }); });
  await page.waitForTimeout(4300);
  await stop('s08_3d');
  await page.click(moreDetail).catch(() => {});
} else {
  await page.click(moreDetail); await page.click('[data-testid="step-drill"]'); await idle(1000);
  await page.click(moreDetail).catch(() => {});
}

if (want('s10')) {
  await page.click('[data-testid="tab-compare"]'); await page.waitForSelector('[data-testid="compare"]'); await page.waitForTimeout(800);
  await page.click('[data-alt="car1_rice_wintercover"]'); await page.waitForTimeout(1200);
  await start();
  await page.waitForTimeout(700);
  await page.click('[data-alt="car2_dryyear_safflower"]');
  await page.waitForTimeout(4000);
  await stop('s10_compare');
}

if (want('s11')) {
  if (!(await page.$('[data-testid="compare"]'))) { await page.click('[data-testid="tab-compare"]'); await page.waitForTimeout(800); }
  await page.click('[data-alt="car2_dryyear_safflower"]').catch(() => {}); await page.waitForTimeout(600);
  await start();
  await page.waitForTimeout(400);
  await page.click('[data-testid="to-brief"]'); await page.waitForSelector('[data-testid="brief-preview"]'); await page.waitForTimeout(900);
  await page.click('[data-testid="brief-preview"]'); await page.waitForSelector('[data-testid="brief"]', { state: 'visible' });
  await page.waitForTimeout(1200);
  const sc = await page.evaluate(async () => {
    const h = [...document.querySelectorAll('[data-testid="brief"] h2')].find((e) => /Check locally/.test(e.textContent));
    let el = h; while (el && !(el.scrollHeight > el.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(el).overflowY))) el = el.parentElement;
    const sc = el || document.scrollingElement;
    if (h) {
      const target = sc.scrollTop + h.getBoundingClientRect().top - (el ? el.getBoundingClientRect().top : 0) - 120;
      const from = sc.scrollTop, t0 = performance.now(), dur = 1500;
      await new Promise((res) => { const step = (now) => { const k = Math.min(1, (now - t0) / dur); const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2; sc.scrollTop = from + (target - from) * e; k < 1 ? requestAnimationFrame(step) : res(); }; requestAnimationFrame(step); });
    }
    return { found: !!h, scroller: el ? el.className : 'document' };
  });
  console.log('  brief', sc);
  await page.waitForTimeout(1500);
  await stop('s11_brief');
}

// Draw a field: overview with the farm catalog pins, then draw a rectangle, acres, name it, the panel fills in
if (want('s12')) {
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__map && window.__map.loaded() && document.querySelector('[data-testid="fields-panel"]'), null, { timeout: 120000 });
  await page.evaluate(() => document.fonts.ready); await idle(2000);
  await start();
  await page.waitForTimeout(900);
  await page.evaluate(() => window.__map.easeTo({ center: [-122.0866, 39.1379], zoom: 15.3, duration: 1600 }));
  await page.waitForTimeout(1800); await idle(600);
  await page.click('[data-testid="draw-btn"]'); await page.waitForTimeout(500);
  const box = { x: 860, y: 300, w: 280, h: 190 };
  await page.mouse.move(box.x, box.y); await page.mouse.down();
  await page.mouse.move(box.x + box.w, box.y + box.h, { steps: 20 }); await page.mouse.up();
  await page.waitForSelector('[data-testid="draw-acres"]', { timeout: 8000 }).catch(() => console.log('  no acres'));
  await page.waitForTimeout(2200);
  console.log('  draw bar', (await page.innerText('[data-testid="draw-bar"]').catch(() => '')).replace(/\s+/g, ' '));
  // not saved: saving on the live app currently crashes the page ("reading 'years'"), so the shot ends on the acres
  await stop('s12_draw');
}
await browser.close();
