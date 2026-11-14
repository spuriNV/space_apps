import type { MeasureKey } from './types';

export const MM_PER_AFAC = 304.8; // 1 acre-ft/acre of water = 304.8 mm depth
export const mmToIn = (mm: number) => mm / 25.4;
export const mmToAfac = (mm: number) => mm / MM_PER_AFAC;
export const haToAc = (ha: number) => ha * 2.47105;
export const fmt = (v: number, d = 0) => v.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });
export const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
export const smoothstep = (a: number, b: number, x: number) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

export const COVER_COLORS: Record<string, string> = { b: '#b07a45', p: '#cfe6a3', c: '#3f9b4b', w: '#5aa7e8', u: '#e8eaed' };
export const COVER_LABELS: Record<string, string> = { b: 'Bare', p: 'Partial cover', c: 'Covered', w: 'Water', u: 'Unknown (cloud)' };

type Stop = [number, string];
export const RAMPS: Record<MeasureKey | 'smap_anomaly' | 'grace_gw_pct', Stop[]> = {
  ndvi: [[0, '#a8672a'], [0.3, '#dcc27c'], [0.55, '#bfdc7a'], [0.78, '#55ae3a'], [1, '#1b7a37']],
  et_mm: [[0, '#e3f0fb'], [0.35, '#9cc8ee'], [0.7, '#4a90d9'], [1, '#174ea6']],
  stress: [[0, '#fdf3c4'], [0.35, '#fbc54d'], [0.65, '#ee7b1c'], [1, '#b3141f']],
  bare_days: [[0, '#f3ead3'], [0.4, '#d9b777'], [0.7, '#b07a45'], [1, '#6f4518']],
  smap_anomaly: [[0, '#a8672a'], [0.45, '#e6cf9a'], [0.75, '#f3f1e7'], [1, '#6fb7c9']],
  grace_gw_pct: [[0, '#8f1d21'], [0.3, '#e26b3d'], [0.6, '#f6c667'], [1, '#fff4c9']],
};
const hex = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
export function ramp(stops: Stop[], t: number): string {
  t = clamp(t, 0, 1);
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [t0, c0] = stops[i - 1], [t1, c1] = stops[i];
      const f = (t - t0) / (t1 - t0 || 1), a = hex(c0), b = hex(c1);
      return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`;
    }
  }
  return stops[stops.length - 1][1];
}
export const rampCss = (stops: Stop[]) => `linear-gradient(90deg, ${stops.map(([t, c]) => `${c} ${t * 100}%`).join(', ')})`;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const MONTH_LETTERS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
export function weekLabel(year: number, week: number) {
  const d = new Date(Date.UTC(year, 0, 1 + Math.floor(week) * 7));
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${year}`;
}
export function dateToWeek(date: string) {
  const d = new Date(date + 'T00:00:00Z');
  const start = Date.UTC(d.getUTCFullYear(), 0, 1);
  return clamp(Math.floor((d.getTime() - start) / (7 * 864e5)), 0, 51);
}
export function fmtDate(date: string) {
  const d = new Date(date + 'T00:00:00Z');
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}
/** month index (0-11) -> first week index, for axis ticks on a 52-week row */
export const monthStartWeek = (m: number) => (m * 52) / 12;

/** Esri World Imagery tile maths for the place-card hero mosaic */
export function tileXY(lon: number, lat: number, z: number) {
  const n = 2 ** z;
  const x = ((lon + 180) / 360) * n;
  const y = ((1 - Math.asinh(Math.tan((lat * Math.PI) / 180)) / Math.PI) / 2) * n;
  return { x, y };
}
export const ESRI_TILE = (z: number, x: number, y: number) =>
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;
