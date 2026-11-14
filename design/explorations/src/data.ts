// Real data, copied from backend outputs (see src/data/*). Helpers turn it into plain-language facts.
import calendar from './data/calendar.json';
import cropHistory from './data/crop_history.json';
import news from './data/news.json';
import riskEvents from './data/risk_events.json';
import strategies from './data/strategies.json';

/* ---------------- cover calendar ---------------- */
export type Cls = 'bare' | 'partial' | 'covered' | 'water' | 'unknown';
export const CLS: Record<Cls, { label: string; color: string; hint: string }> = {
  bare: { label: 'Bare soil', color: '#a8703f', hint: 'greenness below 0.20' },
  partial: { label: 'Thin cover', color: '#b7d77a', hint: 'some plants, greenness 0.20–0.35' },
  covered: { label: 'Crop growing', color: '#2f9e4b', hint: 'greenness above 0.35' },
  water: { label: 'Flooded', color: '#3d97e8', hint: 'standing water seen' },
  unknown: { label: 'No clear view', color: '#6b7280', hint: 'clouds, no image within 30 days' },
};
/** Simple view: bare + thin merged ("exposed" in the engine: cover < 0.5 and not water). */
export const simple = (c: Cls): Cls => (c === 'partial' ? 'bare' : c);
export const SIMPLE_LABEL: Partial<Record<Cls, string>> = { bare: 'Bare or thin', covered: 'Crop growing', water: 'Flooded', unknown: 'No clear view' };

export interface Seg { start_doy: number; end_doy: number; days: number; class: string }
export interface YearCal { year: number; segments: Seg[]; markers: { date: string; type: string }[]; summary: { days_by_class: Record<Cls, number> } }
export const CAL = calendar.years as unknown as YearCal[];
export const YEARS = CAL.map((y) => y.year);
export const yearCal = (y: number) => CAL.find((c) => c.year === y)!;
export const daysIn = (y: number) => (y % 4 === 0 ? 366 : 365);

export function classAt(year: number, doy: number): Cls {
  const s = yearCal(year)?.segments.find((g) => doy >= g.start_doy && doy <= g.end_doy);
  return (s?.class as Cls) ?? 'unknown';
}
export const isExposed = (c: Cls) => c === 'bare' || c === 'partial';

/* ---------------- dates ---------------- */
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const MONTH_START = (y: number) => MONTHS.map((_, m) => doyOf(`${y}-${String(m + 1).padStart(2, '0')}-01`));
export function doyOf(date: string) {
  const d = new Date(date + 'T00:00:00Z');
  return Math.round((d.getTime() - Date.UTC(d.getUTCFullYear(), 0, 1)) / 864e5) + 1;
}
export function fmtDate(date: string, withYear = false) {
  const d = new Date(date + 'T00:00:00Z');
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}${withYear ? ' ' + d.getUTCFullYear() : ''}`;
}
/** "early Jun", "mid Sep", "late Oct" */
export function approxDoy(doy: number, y = 2021) {
  const d = new Date(Date.UTC(y, 0, doy));
  const day = d.getUTCDate();
  return `${day <= 10 ? 'early' : day <= 20 ? 'mid' : 'late'} ${MONTHS[d.getUTCMonth()]}`;
}

/* ---------------- crops on record ---------------- */
const BY_YEAR = cropHistory.by_year as Record<string, string>;
export const cropOf = (y: number) => (BY_YEAR[String(y)]?.startsWith('Fallow') ? 'Fallow (idle)' : BY_YEAR[String(y)] ?? '—');
export const RICE_YEARS = YEARS.filter((y) => cropOf(y) === 'Rice');

/* ---------------- risk events (NASA POWER daily) ---------------- */
export type Risk = 'rain' | 'frost' | 'heat';
export const RISK: Record<Risk, { label: string; rule: string; color: string; unit: string }> = {
  rain: { label: 'Heavy rain', rule: '≥ 25 mm (1 in) in a day', color: '#6cb6ff', unit: 'mm' },
  frost: { label: 'Frost', rule: 'low ≤ 0 °C (32 °F)', color: '#c9f3ff', unit: '°C' },
  heat: { label: 'Extreme heat', rule: 'high ≥ 40 °C (104 °F)', color: '#ff6b5e', unit: '°C' },
};
export interface RiskEvent { date: string; type: Risk; value: number; year: number; doy: number; cls: Cls; exposed: boolean }
export const EVENTS: RiskEvent[] = (riskEvents.events as { date: string; type: Risk; value: number }[]).map((e) => {
  const year = +e.date.slice(0, 4);
  const doy = doyOf(e.date);
  const cls = classAt(year, doy);
  return { ...e, year, doy, cls, exposed: isExposed(cls) };
});
export const eventsIn = (y: number, t?: Risk) => EVENTS.filter((e) => e.year === y && (!t || e.type === t));

/* ---------------- news ---------------- */
export interface News { date: string; title: string; source: string; url: string }
const TRUSTED = ['science.nasa.gov', 'CalMatters', 'Sacramento Bee', 'appeal-democrat.com', 'NBC Bay Area', 'ktvu.com', 'Capitol Weekly', 'KRCR', 'Record Searchlight', 'abc10.com'];
export const NEWS: News[] = (news as News[]).filter((n) => TRUSTED.includes(n.source)).sort((a, b) => a.date.localeCompare(b.date));
export const newsIn = (y: number) => NEWS.filter((n) => n.date.startsWith(String(y)));

/* ---------------- per-year facts ---------------- */
export function yearFacts(y: number) {
  const d = yearCal(y).summary.days_by_class;
  const ev = eventsIn(y);
  const hit = (t: Risk) => ev.filter((e) => e.type === t && e.exposed);
  return {
    year: y, crop: cropOf(y), days: d, exposedDays: d.bare + d.partial,
    rain: ev.filter((e) => e.type === 'rain'), rainHit: hit('rain'),
    frost: ev.filter((e) => e.type === 'frost'), frostHit: hit('frost'),
    heat: ev.filter((e) => e.type === 'heat'), heatHit: hit('heat'),
  };
}

/** Typical rice year: median start/end of the main crop-cover stretch (longest 'covered' run starting after 1 May). */
export const TYPICAL = (() => {
  const runs = RICE_YEARS.map((y) => yearCal(y).segments.filter((s) => s.class === 'covered' && s.start_doy > 120).sort((a, b) => b.days - a.days)[0]).filter(Boolean);
  const med = (a: number[]) => a.sort((x, z) => x - z)[Math.floor(a.length / 2)];
  const start = med(runs.map((r) => r.start_doy));
  const end = med(runs.map((r) => r.end_doy));
  const exposedAvg = Math.round(RICE_YEARS.reduce((s, y) => s + yearFacts(y).exposedDays, 0) / RICE_YEARS.length);
  return { start, end, exposedAvg, coverDays: end - start + 1 };
})();
export const ALL_RAIN = EVENTS.filter((e) => e.type === 'rain');
export const ALL_RAIN_HIT = ALL_RAIN.filter((e) => e.exposed);

/* ---------------- rotations (engine output) ---------------- */
export interface Num { v: number | null; lo: number | null; hi: number | null; verified: boolean; method: string; blocked?: boolean }
export interface Strategy {
  id: string; name: string; baseline: boolean; cycle_years: number; allocation_rule: string | null;
  calendar: { year: number; crop_id: string; plant: string; harvest: string; role: string }[];
  composite: Num & { rank: number; ties_with: string[]; weights: Record<string, number> };
  scores: Record<string, Num>;
  water: Record<'irrigation_need_mm' | 'irrigation_need_af_ac' | 'etc_mm_season', Num>;
  exposure: Record<'bare_days_per_year' | 'exposed_rain_days' | 'exposed_frost_days' | 'exposed_heat_days', Num>;
  replay: Record<'2022' | '2023', Record<'exposed_rain_days' | 'exposed_heat_days' | 'irrigation_need_mm', Num>>;
  local_review: { item: string; severity: string }[];
  gaps: string[];
}
export const STRATS = strategies as unknown as Strategy[];
export const SHORT: Record<string, string> = {
  car0_rice_winterflood: 'Today: rice, winter flood',
  car1_rice_wintercover: 'Rice + winter cover crop',
  car2_dryyear_safflower: 'Dry-year safflower',
  car3_rice_wheat: 'Rice, then wheat',
};
export const PLAIN: Record<string, string> = {
  car0_rice_winterflood: 'Rice every summer; checks flooded over winter.',
  car1_rice_wintercover: 'Rice every summer; cereal + vetch cover over winter instead of a flood.',
  car2_dryyear_safflower: 'When water allocation is under 50%: safflower instead of rice.',
  car3_rice_wheat: 'Two-year cycle: rice one year, winter wheat the next.',
};
export const TODAY = STRATS.find((s) => s.baseline)!;
export const ALTS = STRATS.filter((s) => !s.baseline);

/** The brief's six priorities (+ extras). Higher score = better. */
export const PRIORITIES: { key: string; label: string; plain: string }[] = [
  { key: 'water_use', label: 'Water use', plain: 'needs less irrigation water' },
  { key: 'forage_value', label: 'Forage value', plain: 'grows feed you can cut or graze' },
  { key: 'n_fixation', label: 'Nitrogen fixing', plain: 'legumes add nitrogen to the soil' },
  { key: 'erosion', label: 'Erosion protection', plain: 'less bare soil under heavy rain' },
  { key: 'organic_matter', label: 'Organic matter', plain: 'builds soil carbon' },
  { key: 'market', label: 'Market fit', plain: 'crops you can sell locally' },
];
export const EXTRAS: { key: string; label: string; plain: string }[] = [
  { key: 'pest_break', label: 'Pest-cycle break', plain: 'different crop families' },
  { key: 'infiltration', label: 'Water soaks in', plain: 'roots open the soil' },
  { key: 'n_scavenging', label: 'Holds nitrogen over winter', plain: 'catch crop stops leaching' },
  { key: 'income', label: 'Extra income', plain: 'needs price data' },
];

/* ---------------- ranges and ties ---------------- */
export type Verdict = 'better' | 'worse' | 'unclear' | 'same' | 'none';
/** Compare an alternative's range to today's. higherIsBetter for scores; false for mm / days. */
export function verdict(alt: Num, base: Num, higherIsBetter = true): Verdict {
  if (alt.v == null || base.v == null) return 'none';
  const [aLo, aHi, bLo, bHi] = [alt.lo ?? alt.v, alt.hi ?? alt.v, base.lo ?? base.v, base.hi ?? base.v];
  if (aLo === bLo && aHi === bHi && alt.v === base.v) return 'same';
  if (aLo > bHi) return higherIsBetter ? 'better' : 'worse';
  if (aHi < bLo) return higherIsBetter ? 'worse' : 'better';
  if (aLo === aHi && bLo === bHi) return alt.v > base.v === higherIsBetter ? 'better' : 'worse';
  return 'unclear';
}
/** Share of the narrower range covered by the overlap (spec B4.12 tie rule: > 50% = tie). */
export function overlapShare(a: [number, number], b: [number, number]) {
  const ov = Math.max(0, Math.min(a[1], b[1]) - Math.max(a[0], b[0]));
  const w = Math.min(a[1] - a[0], b[1] - b[0]);
  if (w <= 0) return ov > 0 || (a[0] <= b[1] && b[0] <= a[1]) ? 1 : 0;
  return ov / w;
}
/** Weighted overall score with low/high, as in spec B4.12. */
export function overall(s: Strategy, w: Record<string, number>) {
  let sum = 0, v = 0, lo = 0, hi = 0;
  for (const [k, wi] of Object.entries(w)) {
    const n = s.scores[k];
    if (!wi || !n || n.v == null) continue;
    sum += wi; v += wi * n.v; lo += wi * (n.lo ?? n.v); hi += wi * (n.hi ?? n.v);
  }
  return sum ? { v: v / sum, lo: lo / sum, hi: hi / sum } : { v: 0, lo: 0, hi: 0 };
}
export const DEFAULT_W: Record<string, number> = { water_use: 2, forage_value: 2, n_fixation: 2, erosion: 2, organic_matter: 2, market: 2 };

/* ---------------- units ---------------- */
export const r0 = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-US'));
export const mmIn = (mm: number) => `${r0(mm)} mm (${(mm / 25.4).toFixed(0)} in)`;
export const mmAf = (mm: number) => `${(mm / 304.8).toFixed(1)} acre-ft/acre`;
