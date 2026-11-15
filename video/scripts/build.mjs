// Builds the 30-second CropLytics commercial from stock clips, screen recordings, the voice-over lines and the music.
//   node video/scripts/build.mjs            -> video/croplytics-30s-v2.mp4 + .srt (and stems in video/build/)
//   VO_DIR=/path/to/lines node ...          -> use other voice-over lines (t1.wav ... t9.wav), e.g. ElevenLabs takes
// Needs ffmpeg (no drawtext/libass needed: every super, caption and the end card is rendered to PNG with Chrome).
import { chromium } from '../../design/tools/node_modules/playwright-core/index.mjs';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync, rmSync, symlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const V = join(HERE, '..');
const ROOT = join(V, '..');
const RAW = join(V, 'raw');
const B = join(V, 'build');
const VO_DIR = process.env.VO_DIR ?? join(RAW, 'vo');
const OUT = join(V, process.env.OUT_NAME ?? 'croplytics-30s-v2');
const FPS = 24;
const TOTAL = 29.5; // seconds; 708 frames, under the 30 s limit with margin
for (const d of [B, join(B, 'seg'), join(B, 'ov')]) mkdirSync(d, { recursive: true });

const ff = (args) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], { stdio: ['ignore', 'inherit', 'inherit'] });
const probe = (f) => +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString().trim();

// ---------------------------------------------------------------- shot list (as built; see docs/video-30s.md)
const stock = (f) => join(RAW, 'stock', f);
const rec = (f) => join(RAW, 'rec', f);
// warm, low-saturation grade for the stock footage only (the app's recordings stay ungraded)
const GRADE = "colortemperature=temperature=5400:mix=0.55,eq=contrast=1.05:saturation=0.86:gamma=1.02,curves=all='0/0.035 0.5/0.52 1/0.98'";
const SHOTS = [
  { id: '01_iss', len: 1.75, still: join(ROOT, 'data/cache/car_colusa_rice/iss/ISS062-E-81143.jpg'), crop: [5568, 3132, 0, 330],
    zoom: [1.0, 1.07], c: [0.52, 0.48], grade: "colortemperature=temperature=4800:mix=0.7,eq=contrast=1.7:brightness=-0.05:saturation=1.5:gamma=0.9" },
  { id: '02_look', len: 2.0, src: stock('mixkit-521-1080.mp4'), in: 6.0, zoom: [1.0, 1.06], c: [0.4, 0.5], grade: GRADE },
  { id: '03_hat', len: 1.5, src: stock('mixkit-42382-1080.mp4'), in: 0.6, zoom: [1.0, 1.03], c: [0.5, 0.5], grade: GRADE },
  { id: '04_phone_hand', len: 0.5, src: stock('mixkit-594-1080.mp4'), in: 2.2, zoom: [2.0, 2.04], c: [0.44, 0.62], grade: GRADE },
  { id: '05_phone_app', len: 3.5, phone: rec('s05_phone_cfr.mp4') },
  { id: '06_laptop', len: 0.5, src: stock('mixkit-32139-720.mp4'), in: 1.2, zoom: [1.0, 1.03], c: [0.5, 0.5], grade: GRADE },
  { id: '07_week', len: 2.5, src: rec('s07_week.mp4'), in: 0.5, zoom: [1.3, 1.36], c: [0.2, 0.55] },
  { id: '08_3d', len: 2.5, src: rec('s08_3d.mp4'), in: 4.3, zoom: [1.0, 1.04], c: [0.62, 0.5] },
  { id: '09_nation', len: 2.5, src: rec('s09_nation.mp4'), in: 2.6, zoom: [1.2, 1.26], c: [0.2, 0.5] },
  { id: '10_compare', len: 4.0, src: rec('s10_compare.mp4'), in: 0.2, zoom: [1.0, 1.3], c: [0.0, 0.12] },
  { id: '11_brief', len: 3.0, src: rec('s11_brief.mp4'), in: 2.2, zoom: [1.1, 1.15], c: [0.5, 0.5] },
  { id: '12_draw', len: 2.0, src: rec('s12_draw.mp4'), pieces: [[0.3, 0.5], [4.8, 1.5]], zoom: [1.0, 1.0], c: [0.5, 0.5] },
  { id: '13_end', len: 3.25, card: true },
];
let t = 0; for (const s of SHOTS) { s.start = t; t += s.len; }
if (Math.abs(t - TOTAL) > 1e-6) throw new Error(`shots sum to ${t}, not ${TOTAL}`);
const at = (id) => SHOTS.find((s) => s.id === id).start;

// phone shot: three pieces of the simulator recording (tap, flown in with data, sheet slides up); times in the recording
const PHONE_PIECES = JSON.parse(process.env.PHONE_PIECES ?? '[[32.0,1.4],[39.0,0.5],[42.2,1.6]]');

// ---------------------------------------------------------------- voice-over (separate stem) and captions
const VO = [
  { at: 1.90, text: 'Every season, the same question.' },
  { at: 4.30, text: 'What do I plant next?' },
  { at: 5.85, text: 'CropLytics reads your field with NASA Earth data.' },
  { at: 9.80, text: 'This week, in your field.' },
  { at: 12.30, text: 'From the crop down to the groundwater.' },
  { at: 14.80, text: 'If the water stops, what holds?' },
  { at: 17.35, text: 'What a switch costs: about two acre-feet, not five.' },
  { at: 21.35, text: 'One page, checked against OpenET.' },
  { at: 26.30, text: 'CropLytics. Your field. Your call.', noBurn: true }, // the end card itself says it
];
VO.forEach((l, i) => { l.file = join(VO_DIR, `t${i + 1}.wav`); l.dur = probe(l.file); l.end = l.at + l.dur; });
// a caption stays up 0.35 s after its line, but never past the next line's start
VO.forEach((l, i) => { l.capEnd = Math.min(l.end + 0.35, i + 1 < VO.length ? VO[i + 1].at - 0.1 : TOTAL); });
VO.forEach((l, i) => { if (i + 1 < VO.length && l.end > VO[i + 1].at - 0.05) throw new Error(`VO line ${i + 1} runs into the next (${l.end.toFixed(2)} > ${VO[i + 1].at})`); });
if (VO.at(-1).end > TOTAL - 0.3) throw new Error('last VO line runs past the end');

// ---------------------------------------------------------------- on-screen text (rendered to PNG)
const FIELD = process.env.FIELD_NAME ?? 'Rice field 4 miles east of Williams';
const N_CA = process.env.N_CA ?? '14'; // California fields in the live app's pick list (15 Nov 2026: 14 CA + 1 BC)
const OV = [
  // ISS opener
  { kind: 'super', text: 'The Sacramento Valley, seen from the International Space Station', t: [0.25, at('02_look') - 0.05] },
  { kind: 'credit', text: 'ISS astronaut photo ISS062-E-81143, 4 March 2020. Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center.', t: [0.25, at('02_look') - 0.05] },
  // phone (source line sits left, clear of the phone)
  { kind: 'lower', hi: true, eyebrow: `A real field: one of ${N_CA} in California, plus one in British Columbia`, text: `${FIELD} · 149 acres · Colusa County`, t: [at('05_phone_app') + 0.6, at('06_laptop')] },
  { kind: 'source', left: true, text: 'NASA HLS (Landsat + ESA Sentinel-2) · NASA GPM IMERG rain', t: [at('05_phone_app') + 0.6, at('06_laptop')] },
  // this week
  { kind: 'lower', eyebrow: 'Plan the week', text: 'Irrigation and field access, day by day', t: [at('07_week') + 0.3, at('08_3d')] },
  // nation tools
  { kind: 'lower', eyebrow: 'Nation tools · drought rotation', text: 'Water stops Aug 15: share of crop water still needed', t: [at('09_nation') + 0.2, at('10_compare')] },
  { kind: 'source', text: 'Estimates from the rotation model, not a guarantee', t: [at('09_nation') + 0.2, at('10_compare')] },
  // 3D
  { kind: 'lower', eyebrow: 'Different observations, different scales', text: 'Crop · soil moisture · groundwater in the basin', t: [at('08_3d') + 0.3, at('09_nation')] },
  { kind: 'source', text: process.env.SRC_3D ?? 'ESA Sentinel-2 · NASA GRACE-FO', t: [at('08_3d') + 0.3, at('09_nation')] },
  // compare
  { kind: 'big', eyebrow: 'Compare rotations · reveal trade-offs', text: 'Dry-year safflower: about 2 acre-ft/acre, an upper bound.<br>Rice today: about 5.', t: [at('10_compare') + 0.9, at('11_brief')] },
  { kind: 'source', text: 'Rotation model driven by NASA POWER weather', t: [at('10_compare') + 0.9, at('11_brief')] },
  // brief + the check
  { kind: 'big', eyebrow: 'One page for the grower and adviser', text: 'Water estimate checked against OpenET:<br>runs 16–21% high, nothing tuned.', t: [at('11_brief') + 0.3, at('12_draw')] },
  // draw a field
  { kind: 'lower', eyebrow: 'Any field, not only ours', text: 'Draw a shape, see its acres', t: [at('12_draw') + 0.5, at('13_end')] },
  // end card layers (fade in one after another, then hold still)
  { kind: 'endbg', t: [at('13_end'), TOTAL], fade: 0.4, fadeOut: 0 },
  { kind: 'endmark', t: [at('13_end') + 0.3, TOTAL], fade: 0.5, rise: 12, fadeOut: 0 },
  { kind: 'endline', t: [at('13_end') + 0.6, TOTAL], fade: 0.4, rise: 8, fadeOut: 0 },
  { kind: 'endsmall', t: [at('13_end') + 0.9, TOTAL], fade: 0.4, fadeOut: 0 },
];
for (const l of VO) if (!l.noBurn) OV.push({ kind: 'caption', text: l.text, t: [l.at - 0.05, l.capEnd] });

const font = (f) => readFileSync(join(V, 'fonts', f)).toString('base64');
const CSS = `
@font-face { font-family: 'Zilla Slab'; font-weight: 500; src: url(data:font/ttf;base64,${font('ZillaSlab-Medium.ttf')}); }
@font-face { font-family: 'Zilla Slab'; font-weight: 600; src: url(data:font/ttf;base64,${font('ZillaSlab-SemiBold.ttf')}); }
@font-face { font-family: 'Libre Franklin'; font-weight: 100 900; src: url(data:font/ttf;base64,${font('LibreFranklin-VF.ttf')}); }
:root { --paper: #f7f6f0; --ink: #191c16; --green: #2f5d34; --muted: #5a5e54; --yellow: #ffd166; }
html, body { margin: 0; width: 1920px; height: 1080px; background: transparent; overflow: hidden; }
body { position: relative; font-family: 'Libre Franklin', sans-serif; color: var(--ink); font-variant-numeric: tabular-nums lining-nums; -webkit-font-smoothing: antialiased; }
.box { position: absolute; background: var(--paper); border: 1px solid var(--ink); box-shadow: 2px 2px 0 rgba(25, 28, 22, .35); }
.caption { left: 50%; transform: translateX(-50%); bottom: 44px; font-weight: 600; font-size: 40px; line-height: 1.2; padding: 10px 22px; white-space: nowrap; }
.lower { left: 64px; bottom: 132px; font-weight: 600; font-size: 32px; padding: 12px 20px; }
.big { left: 64px; bottom: 132px; font-family: 'Zilla Slab'; font-weight: 600; font-size: 46px; line-height: 1.15; padding: 16px 24px; border-left: 8px solid var(--green); }
.eyebrow { display: block; font-family: 'Zilla Slab'; font-weight: 600; font-size: 28px; color: var(--green); margin-bottom: 4px; }
.big .eyebrow { font-size: 30px; }
.source.left { right: auto; left: 64px; bottom: 286px; }
.lower.hi { bottom: 330px; }
.source { right: 64px; bottom: 132px; font-size: 21px; color: var(--muted); padding: 7px 14px; background: rgba(247, 246, 240, .94); border-color: rgba(25, 28, 22, .35); box-shadow: none; }
.super { left: 64px; top: 64px; font-family: 'Zilla Slab'; font-weight: 600; font-size: 40px; padding: 10px 20px; }
.credit { left: 64px; right: 64px; bottom: 40px; font-size: 20px; color: var(--muted); padding: 7px 14px; background: rgba(247, 246, 240, .94); border-color: rgba(25, 28, 22, .35); box-shadow: none; }
.endbg { position: absolute; inset: 0; background: var(--paper); }
.endbg::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 6px; background: var(--green); }
.endmark { position: absolute; left: 0; right: 0; top: 270px; text-align: center; font-family: 'Zilla Slab'; font-weight: 600; font-size: 140px; color: var(--green); letter-spacing: -1px; }
.endline { position: absolute; left: 0; right: 0; top: 452px; text-align: center; }
.endline .a { font-family: 'Zilla Slab'; font-weight: 600; font-size: 56px; }
.endline .b { font-size: 36px; margin-top: 14px; }
.endsmall { position: absolute; left: 0; right: 0; top: 640px; text-align: center; font-size: 28px; color: var(--ink); }
.endsmall .cov { margin-bottom: 64px; }
.endsmall .meta { font-size: 26px; color: var(--muted); line-height: 1.6; }
.endsmall .disc { position: absolute; right: 48px; top: 370px; font-size: 20px; color: var(--muted); text-align: right; }
`;
function html(o) {
  switch (o.kind) {
    case 'endbg': return '<div class="endbg"></div>';
    case 'endmark': return '<div class="endmark">CropLytics</div>';
    case 'endline': return '<div class="endline"><div class="a">Your field. Your call.</div><div class="b">Plan next season’s rotation with NASA Earth data.</div></div>';
    case 'endsmall': return `<div class="endsmall"><div class="cov">${N_CA} real California fields and one in British Columbia. Next: co-design with First Nations farmers.</div>
      <div class="meta">NASA Space Apps Challenge 2026 · Field Shift: Adapting Farms with NASA Data<br>croplytics.xyz</div>
      <div class="disc">Voice-over is synthetic (text-to-speech). Farmer footage: Mixkit stock. App: real screen recordings.</div></div>`;
    default: return `<div class="box ${o.kind}${o.left ? ' left' : ''}${o.hi ? ' hi' : ''}">${o.eyebrow ? `<span class="eyebrow">${o.eyebrow}</span>` : ''}${o.text}</div>`;
  }
}

async function renderOverlays() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  // every element on one page; each output frame sets opacities and offsets, and a screenshot is taken only when
  // that state changes (the rest of the 708 frames are links to the same PNG)
  for (const o of OV) if (/—/.test(o.text ?? '')) throw new Error(`em dash in: ${o.text}`);
  await page.setContent(`<!doctype html><html><head><style>${CSS}</style></head><body>${OV.map((o, i) => `<div class="el" id="e${i}" style="position:absolute;inset:0;opacity:0">${html(o)}</div>`).join('')}</body></html>`);
  await page.evaluate(() => document.fonts.ready);
  const dir = join(B, 'ov', 'frames'); rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const N = Math.round(TOTAL * FPS); let prevKey = null, prevFile = null, shots = 0;
  for (let k = 0; k < N; k++) {
    const t = k / FPS;
    const st = OV.map((o) => {
      const [a, b] = o.t, f = o.fade ?? 0.18, fo = o.fadeOut ?? 0.12;
      if (t < a || t >= b) return [0, 0];
      let op = Math.min(1, (t - a) / f); if (fo) op = Math.min(op, (b - t) / fo);
      const dy = o.rise ? o.rise * (1 - Math.min(1, (t - a) / f)) : 0;
      return [Math.round(Math.max(0, op) * 100) / 100, Math.round(dy * 10) / 10];
    });
    const key = JSON.stringify(st);
    const file = join(dir, `${String(k).padStart(4, '0')}.png`);
    if (key !== prevKey) {
      await page.evaluate((st) => st.forEach(([op, dy], i) => { const e = document.getElementById(`e${i}`); e.style.opacity = op; e.style.transform = dy ? `translateY(${dy}px)` : ''; }), st);
      await page.screenshot({ path: file, omitBackground: true }); shots++;
      prevKey = key; prevFile = file;
    } else symlinkSync(prevFile, file);
  }
  console.log(`overlay track: ${N} frames, ${shots} rendered`);
  // phone bezel: paper outside, dark rounded bezel, transparent screen; screen 600 px wide at (1180, 64)
  const P = { x: 1160, y: 60, w: 600, r: 64, bez: 18 };
  P.h = Math.round(P.w * 2556 / 1178);
  await page.setContent(`<!doctype html><html><head><style>html,body{margin:0;width:1920px;height:1080px;background:transparent;overflow:hidden}</style></head><body>
    <svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
      <defs><mask id="m"><rect width="1920" height="1080" fill="white"/><rect x="${P.x}" y="${P.y}" width="${P.w}" height="${P.h}" rx="${P.r - P.bez}" fill="black"/></mask></defs>
      <rect width="1920" height="1080" fill="#f7f6f0" mask="url(#m)"/>
      <rect x="${P.x - P.bez}" y="${P.y - P.bez}" width="${P.w + 2 * P.bez}" height="${P.h + 2 * P.bez}" rx="${P.r}" fill="#1c1d1a" mask="url(#m)"/>
      <rect x="${P.x - P.bez - 1}" y="${P.y - P.bez - 1}" width="${P.w + 2 * P.bez + 2}" height="${P.h + 2 * P.bez + 2}" rx="${P.r + 1}" fill="none" stroke="#8a8c84" stroke-width="2"/>
    </svg></body></html>`);
  await page.screenshot({ path: join(B, 'ov', 'phone_bezel.png'), omitBackground: true });
  await browser.close();
  return P;
}

// ---------------------------------------------------------------- picture
function zoomFilter(s, n) {
  const [z0, z1] = s.zoom ?? [1, 1];
  const [cx, cy] = s.c ?? [0.5, 0.5];
  const z = `(${z0}+(${z1 - z0})*on/${Math.max(n - 1, 1)})`;
  return `zoompan=z='${z}':x='max(0,min(iw-iw/zoom,${cx}*iw-iw/zoom/2))':y='max(0,min(ih-ih/zoom,${cy}*ih-ih/zoom/2))':d=1:s=1920x1080:fps=${FPS}`;
}
function buildSegment(s, P) {
  const n = Math.round(s.len * FPS);
  const out = join(B, 'seg', `${s.id}.mp4`);
  const enc = ['-frames:v', String(n), '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-r', String(FPS), out];
  if (s.still) {
    const [cw, ch, cx0, cy0] = s.crop;
    ff(['-loop', '1', '-framerate', String(FPS), '-t', String(s.len + 1), '-i', s.still, '-vf',
      `crop=${cw}:${ch}:${cx0}:${cy0},scale=3840:2160:flags=lanczos,${s.grade},${zoomFilter(s, n)},format=yuv420p`, ...enc]);
  } else if (s.phone) {
    // pieces of the simulator recording -> 600 px wide screen behind the bezel on paper, slow 3% push
    const parts = PHONE_PIECES.map(([a, d], i) => `[0:v]trim=start=${a}:duration=${d},setpts=PTS-STARTPTS,fps=${FPS},scale=${P.w}:${P.h}:flags=lanczos,setsar=1[p${i}]`).join(';');
    const cat = PHONE_PIECES.map((_, i) => `[p${i}]`).join('') + `concat=n=${PHONE_PIECES.length}:v=1:a=0[scr]`;
    ff(['-i', s.phone, '-loop', '1', '-i', join(B, 'ov', 'phone_bezel.png'), '-f', 'lavfi', '-i', `color=c=0xf7f6f0:s=1920x1080:r=${FPS}:d=${s.len + 1}`, '-filter_complex',
      `${parts};${cat};[2:v][scr]overlay=${P.x}:${P.y}:shortest=0[a];[a][1:v]overlay=0:0,trim=duration=${s.len + 0.5},${zoomFilter({ zoom: [1.0, 1.03], c: [0.62, 0.42] }, n)},format=yuv420p[v]`,
      '-map', '[v]', ...enc]);
  } else if (s.card) {
    ff(['-f', 'lavfi', '-i', `color=c=0xf7f6f0:s=1920x1080:r=${FPS}:d=${s.len}`, '-vf', 'format=yuv420p', ...enc]);
  } else if (s.pieces) {
    const parts = s.pieces.map(([a, d], i) => `[0:v]trim=start=${a}:duration=${d},setpts=PTS-STARTPTS,fps=${FPS},scale=1920:1080:flags=lanczos,setsar=1[p${i}]`).join(';');
    const cat = s.pieces.map((_, i) => `[p${i}]`).join('') + `concat=n=${s.pieces.length}:v=1:a=0,format=yuv420p[v]`;
    ff(['-i', s.src, '-filter_complex', `${parts};${cat}`, '-map', '[v]', ...enc]);
  } else {
    const pre = s.grade ? `,${s.grade}` : '';
    ff(['-ss', String(s.in), '-i', s.src, '-vf', `fps=${FPS},scale=3840:2160:flags=lanczos${pre},${zoomFilter(s, n)},format=yuv420p`, ...enc]);
  }
  const got = +execFileSync('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', out]).toString().trim().replace(/,$/, '');
  if (got !== n) throw new Error(`${s.id}: ${got} frames, wanted ${n}`);
  return out;
}

// ---------------------------------------------------------------- sound
function buildAudio() {
  const vo = join(B, 'vo.wav'), music = join(B, 'music.wav'), mix = join(B, 'mix.wav');
  // VO stem: each line at its time
  const ins = VO.flatMap((l) => ['-i', l.file]);
  const pl = VO.map((l, i) => `[${i}:a]aresample=48000,aformat=channel_layouts=mono,adelay=${Math.round(l.at * 1000)}:all=1[v${i}]`).join(';');
  ff([...ins, '-filter_complex', `${pl};${VO.map((_, i) => `[v${i}]`).join('')}amix=inputs=${VO.length}:normalize=0,apad,atrim=0:${TOTAL}[o]`, '-map', '[o]', '-ar', '48000', '-ac', '1', vo]);
  // music bed: "Dreaming Big" from 75 s so its own ending lands near 29 s; fades in, rings out
  const M = { file: join(RAW, 'music', 'mixkit-music-31.mp3'), from: 75.0 };
  ff(['-ss', String(M.from), '-t', String(TOTAL), '-i', M.file, '-af', `aresample=48000,afade=t=in:st=0:d=1.2,afade=t=out:st=${TOTAL - 2.2}:d=2.2,volume=-12dB`, '-ac', '2', music]);
  // duck the music about 9 dB under the voice, then mix and normalise the whole spot to -14 LUFS
  const graph = `[1:a]asplit=2[sc][vom];[0:a][sc]sidechaincompress=threshold=0.015:ratio=8:attack=30:release=350:makeup=1[duck];[vom]pan=stereo|c0=c0|c1=c0[vos];[duck][vos]amix=inputs=2:normalize=0:weights='1 1'[m]`;
  ff(['-i', music, '-i', vo, '-filter_complex', graph, '-map', '[m]', '-ar', '48000', join(B, 'premix.wav')]);
  return { vo, music, mix, premix: join(B, 'premix.wav') };
}
function loudnorm(src, dst) {
  const r = execFileSync('sh', ['-c', `ffmpeg -hide_banner -i "${src}" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1`]).toString();
  const j = JSON.parse(r.slice(r.lastIndexOf('{'), r.lastIndexOf('}') + 1));
  ff(['-i', src, '-af', `loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=${j.input_i}:measured_TP=${j.input_tp}:measured_LRA=${j.input_lra}:measured_thresh=${j.input_thresh}:offset=${j.target_offset}:linear=true,aresample=48000`, '-ar', '48000', dst]);
}

// ---------------------------------------------------------------- captions file
function srt() {
  const ts = (x) => { const ms = Math.round(x * 1000); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60; return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
  return VO.map((l, i) => `${i + 1}\n${ts(l.at)} --> ${ts(l.capEnd)}\n${l.text}\n`).join('\n');
}

// ---------------------------------------------------------------- go
const P = await renderOverlays();
console.log(`overlays: ${OV.length}`);
const reuse = (process.env.REUSE ?? '').split(',');
const segs = SHOTS.map((s) => { const f = reuse.includes(s.id) || reuse.includes('all') ? join(B, 'seg', `${s.id}.mp4`) : buildSegment(s, P); console.log('segment', s.id, s.start.toFixed(2), s.len); return f; });
writeFileSync(join(B, 'concat.txt'), segs.map((f) => `file '${f}'`).join('\n') + '\n');
ff(['-f', 'concat', '-safe', '0', '-i', join(B, 'concat.txt'), '-c', 'copy', join(B, 'base.mp4')]);

// one overlay pass: the rendered RGBA track over the cut
ff(['-i', join(B, 'base.mp4'), '-framerate', String(FPS), '-i', join(B, 'ov', 'frames', '%04d.png'), '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]',
  '-map', '[v]', '-frames:v', String(Math.round(TOTAL * FPS)), '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', String(FPS), join(B, 'picture.mp4')]);

const A = buildAudio();
loudnorm(A.premix, A.mix);
writeFileSync(`${OUT}.srt`, srt());
const comment = 'CropLytics, NASA Space Apps Challenge 2026, Field Shift. App footage: real screen recordings of croplytics-app.onrender.com. Farmer footage: Mixkit stock video (human-shot, Mixkit Free License). Music: Mixkit Stock Music Free License. Voice-over: synthetic speech (SI-generated) from Microsoft Edge text-to-speech, en-US-AndrewNeural, placeholder. No AI-generated images or video.';
ff(['-i', join(B, 'picture.mp4'), '-i', A.mix, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest',
  '-metadata', 'title=CropLytics: 30-second commercial (v2)', '-metadata', `comment=${comment}`, '-metadata', `description=${comment}`, '-movflags', '+faststart', `${OUT}.mp4`]);
console.log('wrote', `${OUT}.mp4`, probe(`${OUT}.mp4`).toFixed(3), 's');
