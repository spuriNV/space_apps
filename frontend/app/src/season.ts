// Grower-unit summaries computed from the API's daily weather (NOAA station means, NASA POWER reference ET)
// and the satellite calendar. Pure functions; every result says which season it describes and how "normal" was built.
import type { Calendar, RotationStrategy } from './types';
import { MONTHS, dekadOf, yearOf } from './lib';

export interface DailyRow { date: string; precip_mm: number | null; eto_mm: number | null; ncei_precip_mm: number | null; ncei_tmax_c: number | null; ncei_tmin_c: number | null; imerg_precip_mm?: number | null; grace_gw_pct?: number | null;
  /** BC: Environment and Climate Change Canada station values (the ncei_* columns are null there) */
  eccc_tmax_c?: number | null; eccc_tmin_c?: number | null; eccc_precip_mm?: number | null }
export interface Daily { rows: DailyRow[]; first: string; last: string }
/** The daily record restricted to days that have `key` (each source has its own end date: stations stop in Dec 2025, NASA IMERG and POWER run to this week). */
export function only(daily: Daily, key: keyof DailyRow): Daily | null {
  const rows = daily.rows.filter((r) => r[key] != null);
  return rows.length ? { rows, first: rows[0].date, last: rows[rows.length - 1].date } : null;
}
/** Weather-station readings: NOAA stations in California, ECCC stations in BC. */
export const stTmax = (r: DailyRow) => r.ncei_tmax_c ?? r.eccc_tmax_c ?? null;
export const stTmin = (r: DailyRow) => r.ncei_tmin_c ?? r.eccc_tmin_c ?? null;
export const stPrecip = (r: DailyRow) => r.ncei_precip_mm ?? r.eccc_precip_mm ?? null;
/** The daily record restricted to days where `f` has a value. */
function onlyBy(daily: Daily, f: (r: DailyRow) => number | null | undefined): Daily | null {
  const rows = daily.rows.filter((r) => f(r) != null);
  return rows.length ? { rows, first: rows[0].date, last: rows[rows.length - 1].date } : null;
}
/** Daily rain: NASA GPM IMERG over the field when present, else the station mean. */
export const rainOf = (r: DailyRow) => r.imerg_precip_mm ?? stPrecip(r);

/** Heat threshold for every hot-day count in the app: 104 °F (40 °C), NOAA station highs (PLAN.md decisions, 14 Nov). */
export const HOT_C = 40, HOT_F = 104;

const MONTH_END = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const pad = (n: number) => String(n).padStart(2, '0');
/** Last day covered by the 10-day step t, as YYYY-MM-DD. */
export function cutoffOf(t: number) {
  const y = yearOf(t), d = dekadOf(t), m = Math.floor(d / 3);
  const day = d % 3 === 0 ? 10 : d % 3 === 1 ? 20 : MONTH_END[m] + (m === 1 && y % 4 === 0 ? 1 : 0);
  return `${y}-${pad(m + 1)}-${pad(day)}`;
}
const mmdd = (iso: string) => iso.slice(5);
const inch = (mm: number) => mm / 25.4;
const F = (c: number) => (c * 9) / 5 + 32;
const fmtShort = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };

/** Season boundaries: the rain season (water year) runs 1 Oct to 30 Sep; heat and crop water use run with the calendar year. */
const wyStart = (iso: string) => { const y = +iso.slice(0, 4); return +iso.slice(5, 7) >= 10 ? y : y - 1; };
const sumWhere = (rows: DailyRow[], from: string, to: string, f: (r: DailyRow) => number | null) => {
  let s = 0, n = 0;
  for (const r of rows) { if (r.date < from || r.date > to) continue; const v = f(r); if (v != null) { s += v; n++; } }
  return { s, n };
};

export interface Period { label: string; from: string; to: string; current: boolean }
/** The period "so far" for the timeline date, or the last complete one if the daily record stops before it. */
function periodFor(daily: Daily, t: number, kind: 'water' | 'calendar'): Period {
  const cut = cutoffOf(t);
  const startY = kind === 'water' ? wyStart(cut) : +cut.slice(0, 4);
  const from = kind === 'water' ? `${startY}-10-01` : `${startY}-01-01`;
  if (daily.last >= cut && daily.first <= from) return { label: kind === 'water' ? `since 1 Oct ${startY}` : `since 1 Jan ${startY}`, from, to: cut, current: true };
  // the record stops inside the current season: count up to its last day and say so
  if (daily.last >= from && daily.first <= from) return { label: `${kind === 'water' ? `1 Oct ${startY}` : `1 Jan ${startY}`} to ${fmtShort(daily.last).replace(/ \d{4}$/, '')}`, from, to: daily.last, current: true };
  // fall back to the last complete season in the record
  const lastY = +daily.last.slice(0, 4);
  if (kind === 'water') { const e = mmdd(daily.last) >= '09-30' ? lastY : lastY - 1; return { label: `last season, Oct ${e - 1} to Sep ${e}`, from: `${e - 1}-10-01`, to: `${e}-09-30`, current: false }; }
  const e = mmdd(daily.last) >= '12-31' ? lastY : lastY - 1;
  return { label: `last year, ${e}`, from: `${e}-01-01`, to: `${e}-12-31`, current: false };
}
/** Same window in every earlier season with full data: the "normal" we compare against. */
function normalOf(daily: Daily, p: Period, f: (r: DailyRow) => number | null, agg: 'sum' | 'count' = 'sum') {
  const y0 = +p.from.slice(0, 4), vals: number[] = [];
  for (let k = 1; k <= 30; k++) {
    const from = `${y0 - k}${p.from.slice(4)}`, to = `${+p.to.slice(0, 4) - k}${p.to.slice(4)}`;
    if (from < daily.first || to > daily.last) continue;
    const { s, n } = sumWhere(daily.rows, from, to, f);
    if (n > 0) vals.push(agg === 'sum' ? s : n);
  }
  return { mean: vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null, n: vals.length, first: y0 - vals.length };
}

export interface RainSoFar { period: Period; inches: number; normal: number | null; nSeasons: number; pct: number | null; source: 'imerg' | 'stations' | 'power' }
/** Rain so far this season: NASA GPM IMERG over the field (runs to this week), normal = the same dates in earlier seasons of IMERG.
 *  Falls back to the NOAA stations when IMERG is missing. */
export function rainSoFar(all: Daily, t: number): RainSoFar | null {
  const im = only(all, 'imerg_precip_mm');
  const st = im ? null : onlyBy(all, stPrecip);
  // a tapped spot has neither IMERG nor stations: NASA POWER's daily rain for the area
  const pw = im || st ? null : only(all, 'precip_mm');
  const daily = im ?? st ?? pw;
  if (!daily) return null;
  const f = (r: DailyRow) => (im ? r.imerg_precip_mm ?? null : st ? stPrecip(r) : r.precip_mm ?? null);
  const p = periodFor(daily, t, 'water');
  const { s } = sumWhere(daily.rows, p.from, p.to, f);
  const nm = normalOf(daily, p, f);
  const inches = inch(s), normal = nm.mean == null ? null : inch(nm.mean);
  return { period: p, inches, normal, nSeasons: nm.n, pct: normal ? (inches / normal) * 100 : null, source: im ? 'imerg' : st ? 'stations' : 'power' };
}

export interface HeatFrost { period: Period; hot: number; hotNormal: number | null; frost: number; frostNormal: number | null; frostPeriod: Period; nSeasons: number }
/** Hot days: station high at or above 104 °F (40 °C), the threshold used everywhere in the app. Frost nights: station low at or below 32 °F, counted over the rain season (Oct to Sep). */
export function heatFrost(all: Daily, t: number): HeatFrost | null {
  const daily = onlyBy(all, stTmax);
  if (!daily) return null;
  const p = periodFor(daily, t, 'calendar'), pf = periodFor(daily, t, 'water');
  const hotF = (r: DailyRow) => { const v = stTmax(r); return v != null && v >= HOT_C ? 1 : null; };
  const frostF = (r: DailyRow) => { const v = stTmin(r); return v != null && F(v) <= 32 ? 1 : null; };
  const hot = sumWhere(daily.rows, p.from, p.to, hotF).n, frost = sumWhere(daily.rows, pf.from, pf.to, frostF).n;
  const hn = normalOf(daily, p, hotF, 'count'), fn = normalOf(daily, pf, frostF, 'count');
  // normalOf skips seasons with zero events (n = 0); recount those as zero
  const zeroFill = (m: { mean: number | null; n: number }, per: Period) => {
    let seasons = 0; const y0 = +per.from.slice(0, 4);
    for (let k = 1; k <= 30; k++) { const from = `${y0 - k}${per.from.slice(4)}`, to = `${+per.to.slice(0, 4) - k}${per.to.slice(4)}`; if (from >= daily.first && to <= daily.last) seasons++; }
    return seasons ? ((m.mean ?? 0) * m.n) / seasons : null;
  };
  return { period: p, hot, hotNormal: zeroFill(hn, p), frost, frostNormal: zeroFill(fn, pf), frostPeriod: pf, nSeasons: hn.n };
}

/** Crop water use so far for today's rotation: the engine's monthly crop water use, scaled by how thirsty this year's weather was
 *  (reference ET from NASA POWER, this year vs the same months on average). A model estimate, not a measurement. */
export function cropWaterSoFar(all: Daily, base: RotationStrategy, t: number) {
  const daily = only(all, 'eto_mm');
  if (!daily) return null;
  const p = periodFor(daily, t, 'calendar');
  const months = base.water.etc_by_month_mm;
  if (!months?.length) return null;
  const endM = +p.to.slice(5, 7), endD = +p.to.slice(8, 10), y = +p.from.slice(0, 4);
  let model = 0, normal = 0;
  for (let m = 1; m <= endM; m++) {
    const share = m < endM ? 1 : endD / MONTH_END[m - 1];
    const mFrom = `${y}-${pad(m)}-01`, mTo = `${y}-${pad(m)}-${pad(m < endM ? MONTH_END[m - 1] : endD)}`;
    const thisY = sumWhere(daily.rows, mFrom, mTo, (r) => r.eto_mm).s;
    const others: number[] = [];
    for (let k = 1; k <= 30; k++) { const yy = y - k; if (`${yy}-${pad(m)}-01` < daily.first) break; others.push(sumWhere(daily.rows, `${yy}-${pad(m)}-01`, `${yy}-${pad(m)}-${pad(m < endM ? MONTH_END[m - 1] : endD)}`, (r) => r.eto_mm).s); }
    const avg = others.length ? others.reduce((a, b) => a + b, 0) / others.length : thisY;
    const etc = months[m - 1] * share;
    normal += etc;
    model += avg > 0 ? etc * (thisY / avg) : etc;
  }
  return { period: p, inches: inch(model), normal: inch(normal), pct: normal ? (model / normal) * 100 : null };
}

/** This winter's bare window from the satellite calendar (Nov to Mar), and how often a 1-inch rain day landed in it before. */
export interface BareWindow { from: string; to: string; days: number; share: number; years: number[]; chance: number | null; winters: number; hits: number; avgDays: number | null }
const WINTER = [30, 31, 32, 33, 34, 35, 0, 1, 2, 3, 4, 5, 6, 7, 8]; // early Nov .. late Mar, in 10-day steps
const PART = ['early', 'mid', 'late'];
const dekadName = (d: number) => `${PART[d % 3]} ${MONTHS[Math.floor(d / 3)]}`;
export function bareWindow(cal: Calendar, daily: Daily | null, years: number[]): BareWindow | null {
  const ys = (cal?.years ?? []).filter((y) => years.includes(y.year) && y.rule.replace(/u/g, '').length > 6);
  if (!ys.length) return null;
  // a winter step counts as "usually bare" when it was bare (greenness below 0.2) in at least half the winters with a clear view
  const bare = WINTER.map((d) => {
    let b = 0, n = 0;
    for (const y of ys) {
      const yy = d >= 30 ? y : (cal?.years ?? []).find((x) => x.year === y.year + 1);
      const c = yy?.rule[d];
      if (!c || c === 'u') continue;
      n++; if (c === 'b') b++;
    }
    return n ? b / n : 0;
  });
  let best: [number, number] | null = null;
  for (let i = 0; i < WINTER.length; i++) {
    if (bare[i] < 0.5) continue;
    let j = i; while (j + 1 < WINTER.length && bare[j + 1] >= 0.5) j++;
    if (!best || j - i > best[1] - best[0]) best = [i, j];
    i = j;
  }
  if (!best) return { from: '', to: '', days: 0, share: 0, years: ys.map((y) => y.year), chance: null, winters: 0, hits: 0, avgDays: null };
  const [a, b] = best, d0 = WINTER[a], d1 = WINTER[b];
  const share = bare.slice(a, b + 1).reduce((x, y) => x + y, 0) / (b - a + 1);
  let winters = 0, hits = 0, total = 0;
  if (daily) {
    for (let y = +daily.first.slice(0, 4); y <= +daily.last.slice(0, 4); y++) {
      const dayOf = (d: number, yy: number) => { const m = Math.floor(d / 3); return [`${yy}-${pad(m + 1)}-${pad([1, 11, 21][d % 3])}`, `${yy}-${pad(m + 1)}-${pad(d % 3 === 2 ? MONTH_END[m] : [10, 20][d % 3])}`]; };
      const [from] = dayOf(d0, d0 >= 30 ? y : y + 1), [, to] = dayOf(d1, d1 >= 30 ? y : y + 1);
      if (from < daily.first || to > daily.last) continue;
      const n = sumWhere(daily.rows, from, to, (r) => { const v = stPrecip(r); return v != null && v >= 25.4 ? 1 : null; }).n;
      winters++; if (n > 0) hits++; total += n;
    }
  }
  return { from: dekadName(d0), to: dekadName(d1), days: (b - a + 1) * 10, share, years: ys.map((y) => y.year), chance: winters ? (hits / winters) * 100 : null, winters, hits, avgDays: winters ? total / winters : null };
}

export const fmtIn = (v: number) => (v < 10 ? v.toFixed(1) : Math.round(v).toString());
export { fmtShort };

/** Hot days (station high >= 104 °F) that land while a rotation leaves the field bare, per year on average.
 *  Uses the rotation's month-by-month cover and NOAA station highs, every full year in the daily record. */
export function hotBareDays(all: Daily, monthCover: string) {
  const daily = onlyBy(all, stTmax);
  if (!daily) return null;
  const y0 = +daily.first.slice(0, 4), y1 = +daily.last.slice(0, 4) - (daily.last.slice(5) >= '12-31' ? 0 : 1);
  const per: number[] = [];
  for (let y = y0; y <= y1; y++) {
    let n = 0, seen = 0;
    for (const r of daily.rows) {
      const tx = stTmax(r);
      if (!r.date.startsWith(String(y)) || tx == null) continue;
      seen++;
      if (tx >= HOT_C && monthCover[+r.date.slice(5, 7) - 1] === 'b') n++;
    }
    if (seen > 300) per.push(n);
  }
  if (!per.length) return null;
  const mean = per.reduce((a, b) => a + b, 0) / per.length;
  return { value: mean, low: Math.min(...per), high: Math.max(...per), years: per.length, from: y0, to: y1 };
}
