import type { Calendar, CellGrid, CellProps, CoverClass, GridLayer, Location } from './types';

export const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
export const T_MAX = YEARS.length * 36 - 1;
/** Today is 14 Nov 2026 (mid November). The app opens on this date. */
export const TODAY_ISO = '2026-11-14';
export const THIS_YEAR = 2026;
/** By default the timeline and calendars show this season plus the last 3; older years sit behind "Show earlier years". */
export const RECENT_FROM = 2023;
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PART = ['Early', 'Mid', 'Late'];

export const tOf = (year: number, dekad: number) => (year - 2016) * 36 + dekad;
export const yearOf = (t: number) => 2016 + Math.floor(t / 36);
export const dekadOf = (t: number) => t % 36;
export const tLabel = (t: number) => { const d = dekadOf(t); return `${PART[d % 3]} ${MONTHS[Math.floor(d / 3)]} ${yearOf(t)}`; };
export const TODAY_T = (2026 - 2016) * 36 + 31;
export const dateToT = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return tOf(y, (m - 1) * 3 + (d <= 10 ? 0 : d <= 20 ? 1 : 2)); };
export const fmtDate = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };

export const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
export const ordinal = (n: number) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };

// dual units (spec B8)
export const haToAc = (ha: number) => ha * 2.47105;
export const mmToIn = (mm: number) => mm / 25.4;
export const afacToMm = (af: number) => af * 304.8;
export const mmToAfac = (mm: number) => mm / 304.8;
/** A dryland rotation: the API marks every crop year in its calendar `irrigated: false`. Its irrigation need is 0 by design. */
export const RAIN_FED = 'Rain-fed (no irrigation)';
export const isRainFed = (s: { calendar?: { irrigated?: boolean }[] }) => !!s.calendar?.length && s.calendar.every((c) => c.irrigated === false);
/** "3.1 acre-ft/acre", or the rain-fed label for a dryland rotation. */
export const needText = (s: { calendar?: { irrigated?: boolean }[] }, af: number) => (isRainFed(s) ? RAIN_FED : `${af.toFixed(1)} acre-ft/acre`);

export const CLASS_LABEL: Record<CoverClass, string> = { b: 'Bare', p: 'Partial cover', c: 'Covered', w: 'Water', u: 'Unknown (cloud)' };
export const CLASS_COLOR: Record<CoverClass, string> = { b: '#a8703f', p: '#b7d77a', c: '#2f9e4b', w: '#3d97e8', u: '#6b7280' };
/** Soil texture (data colours; never used for chrome): sand tan, silt light, clay brown. */
export const SOIL_COLOR = { sand: '#d9b46a', silt: '#e9e3d3', clay: '#7a4a2b' } as const;
export const RISK_COLOR = { rain: '#6cb6ff', frost: '#b8f0ff', heat: '#ff6b5e', dry: '#ffb44a' } as const;
export const RISK_LABEL = { rain: 'Heavy rain', frost: 'Frost', heat: 'Heat', dry: 'Dry spell' } as const;

function hex(c: string) { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
export function ramp(stops: [number, string][], v: number) {
  const x = clamp(v, stops[0][0], stops[stops.length - 1][0]);
  for (let i = 1; i < stops.length; i++) {
    if (x <= stops[i][0]) {
      const [a, ca] = stops[i - 1], [b, cb] = stops[i];
      const t = (x - a) / (b - a || 1), A = hex(ca), B = hex(cb);
      return `rgb(${A.map((p, k) => Math.round(p + (B[k] - p) * t)).join(',')})`;
    }
  }
  return stops[stops.length - 1][1];
}
export const NDVI_RAMP: [number, string][] = [[0.35, '#9fd45f'], [0.6, '#43b04f'], [0.9, '#12733a']];
export const ET_RAMP: [number, string][] = [[0, '#f4e3a0'], [3, '#8fd3a8'], [6, '#2aa7b8'], [9, '#2456d6']];
export const SMAP_RAMP: [number, string][] = [[0, '#b0592a'], [35, '#d8b77a'], [60, '#a5d6cf'], [100, '#17a89c']];
export const GRACE_RAMP: [number, string][] = [[0, '#8e2148'], [30, '#c9688a'], [60, '#9a9fd8'], [100, '#39c4d8']];

/** Last 10-day step with a clear satellite reading (the calendar ends where the processed imagery ends). */
export function lastDataT(cal: Calendar) {
  for (let t = cal.years.length * 36 - 1; t >= 0; t--) { const y = cal.years[Math.floor(t / 36)]; if (y && y.rule[t % 36] && y.rule[t % 36] !== 'u') return t; }
  return 0;
}
/** The date the satellite answers come from: the timeline date, or the latest reading if the timeline is past it. */
export const dataT = (cal: Calendar, t: number) => Math.min(t, lastDataT(cal));
/** Value of a 10-day series at t, holding the last value past the end of the series. */
export const atT = <T,>(vals: T[], t: number): T | undefined => vals[Math.min(t, vals.length - 1)];
/** Latest non-empty value at or before t, and when it was (weekly/monthly NASA products lag a few weeks). */
export function latestAt(vals: (number | null)[], t: number, maxBack = 12): { v: number; t: number } | null {
  for (let k = Math.min(t, vals.length - 1); k >= 0 && t - k <= maxBack; k--) if (vals[k] != null) return { v: vals[k] as number, t: k };
  return null;
}

export interface FieldState { cls: CoverClass; ndvi: number; et: number; disagree: boolean; ruleCls: CoverClass; mlCls: CoverClass }
export function fieldState(cal: Calendar, t: number, detector: 'rule' | 'ml'): FieldState {
  const y = cal.years[Math.floor(t / 36)], d = t % 36;
  if (!y) return { cls: 'u', ndvi: 0, et: 0, disagree: false, ruleCls: 'u', mlCls: 'u' };
  const ruleCls = y.rule[d] as CoverClass, mlCls = y.ml[d] as CoverClass;
  return { cls: detector === 'rule' ? ruleCls : mlCls, ndvi: y.ndvi[d], et: y.et_mm_day[d], disagree: ruleCls !== mlCls, ruleCls, mlCls };
}

export interface CellState { cls: CoverClass; ndvi: number; et: number }
/** Per-cell value = field value for the date x the cell's fixed spatial offset (mock/cells.json). */
export function cellState(loc: Location, fs: FieldState, c: CellProps): CellState {
  let cls = fs.cls, ndvi: number;
  const partialFlood = loc.id === 'caf_tulare_forage';
  if (cls === 'u') return { cls, ndvi: 0, et: 0 };
  if (cls === 'w' && partialFlood && c.low < 0.38) cls = c.low < 0.2 ? 'p' : 'b';
  if (cls === 'w') ndvi = 0.02 + 0.02 * c.v;
  else if (cls === 'b') ndvi = 0.14 + 0.04 * c.v;
  else if (fs.cls === 'w') ndvi = cls === 'p' ? 0.27 : 0.15;
  else ndvi = clamp(fs.ndvi * (1 + 0.32 * c.v) - (c.edge ? 0.05 : 0), 0.05, 0.93);
  if (cls !== 'w') cls = ndvi < 0.2 ? 'b' : ndvi < 0.35 ? 'p' : 'c';
  const et = clamp(fs.et * (cls === 'w' ? 1 : 1 + 0.28 * c.v), 0.05, 9.5);
  return { cls, ndvi, et };
}
export function cellColor(s: CellState, c: CellProps, metric: 'cover' | 'et') {
  if (s.cls === 'u') return '#7b818c';
  if (metric === 'et') return ramp(ET_RAMP, s.et);
  if (s.cls === 'w') return ramp([[-1, '#2f86db'], [1, '#56aaf0']], c.v);
  if (s.cls === 'b') return ramp([[-1, '#8f5c30'], [1, '#bd8650']], c.v);
  if (s.cls === 'p') return ramp([[0.2, '#cfd98a'], [0.35, '#a9d46c']], s.ndvi);
  return ramp(NDVI_RAMP, s.ndvi);
}
/** 0..1 extrusion height */
export function cellHeight(s: CellState, metric: 'cover' | 'et') {
  if (s.cls === 'u') return 0.03;
  if (metric === 'et') return s.et / 9;
  if (s.cls === 'w') return 0.02;
  return clamp(s.ndvi, 0.05, 1);
}

/** Tie rule (spec B4.12): interval overlap > 50% of the narrower range. */
export function overlapShare(a: { low: number | null; high: number | null }, b: { low: number | null; high: number | null }) {
  const al = a.low ?? 0, ah = a.high ?? 0, bl = b.low ?? 0, bh = b.high ?? 0;
  const o = Math.min(ah, bh) - Math.max(al, bl);
  const w = Math.min(ah - al, bh - bl);
  return w <= 0 ? 0 : clamp(o / w, 0, 1);
}

/** Real 30 m grid (backend/field grid.geojson): pick the layer for the scrubber date.
 *  A single clear scene within 12 days wins; otherwise the quarter median for that year. */
export function gridLayerFor(cells: CellGrid, t: number): GridLayer | null {
  if (!cells.layers) return null;
  const y = yearOf(t), d = dekadOf(t), m = Math.floor(d / 3) + 1, day = [5, 15, 25][d % 3];
  const tt = Date.UTC(y, m - 1, day);
  const scene = cells.layers.find((l) => l.kind === 'scene' && l.date && Math.abs(Date.parse(l.date) - tt) <= 12 * 864e5);
  return scene ?? cells.layers.find((l) => l.kind === 'quarter_median' && l.year === y && l.quarter === Math.floor((m - 1) / 3) + 1) ?? null;
}
export const gridLayerLabel = (l: GridLayer | null) => !l ? 'no image for this date' : l.kind === 'scene' ? `image of ${fmtDate(l.date!)}` : `${['Jan–Mar', 'Apr–Jun', 'Jul–Sep', 'Oct–Dec'][(l.quarter ?? 1) - 1]} ${l.year}, middle of ${l.n_scenes} image${l.n_scenes === 1 ? '' : 's'}`;
export function realCellState(c: CellProps, layer: GridLayer | null, fs: FieldState): CellState {
  const v = layer ? c.nd?.[layer.key] : null;
  if (v == null) return { cls: 'u', ndvi: 0, et: 0 };
  const cls: CoverClass = fs.cls === 'w' ? 'w' : v < 0.2 ? 'b' : v <= 0.35 ? 'p' : 'c';
  return { cls, ndvi: v, et: clamp(fs.et, 0.05, 9.5) };
}
