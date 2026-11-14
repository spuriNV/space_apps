import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
await p.goto('https://maplibre.org/maplibre-gl-js/docs/examples/3d-terrain/', { waitUntil: 'networkidle', timeout: 60000 }).catch(e => console.log('nav', e.message));
await p.waitForTimeout(4000);
await p.screenshot({ path: process.argv[2] });
await b.close();
console.log('ok');
