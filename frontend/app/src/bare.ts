// One definition of "bare" for every screen (field panel, year, compare, coming season, brief):
// bare = satellite greenness (NDVI) below 0.2 and not under water. The same threshold the rotation model uses.
// Today's rotation uses what the satellites saw; alternatives use the rotation model's estimate, labelled as such.
import type { Calendar, CalendarYear } from './types';
import { MONTHS, lastDataT, yearOf } from './lib';

export const BARE_DEF = 'Bare = satellite greenness below 0.2 and not under water.';

/** Bare days in one calendar year, scaled up for the 10-day steps with no clear view. Null when under half the year was seen. */
export function bareDaysYear(y: CalendarYear): number | null {
  const steps = y.rule.split('');
  const clear = steps.filter((c) => c !== 'u').length;
  if (clear < 18) return null;
  return Math.round((steps.filter((c) => c === 'b').length / clear) * 365);
}

/** Satellite-seen bare days a year for the field's own rotation: the last 3 processed years. */
export function observedBare(cal: Calendar | null): { value: number; years: number[]; per: Record<number, number> } | null {
  if (!cal) return null;
  const last = yearOf(lastDataT(cal));
  const per: Record<number, number> = {};
  for (const y of cal.years) { if (y.year > last - 3 && y.year <= last) { const v = bareDaysYear(y); if (v != null) per[y.year] = v; } }
  const ys = Object.keys(per).map(Number);
  if (!ys.length) return null;
  return { value: Math.round(ys.reduce((a, y) => a + per[y], 0) / ys.length), years: ys, per };
}

/** When the field is usually bare: months that were bare in at least half of the recent clear years. */
export function usuallyBareMonths(cal: Calendar | null): string {
  if (!cal) return '';
  const last = yearOf(lastDataT(cal));
  const ys = cal.years.filter((y) => y.year > last - 3 && y.year <= last);
  const months = MONTHS.map((_, m) => {
    let b = 0, n = 0;
    for (const y of ys) for (let k = 0; k < 3; k++) { const c = y.rule[m * 3 + k]; if (c && c !== 'u') { n++; if (c === 'b') b++; } }
    return n ? b / n >= 0.5 : false;
  });
  if (!months.some(Boolean)) return 'rarely bare';
  // group consecutive months, wrapping December into January
  const runs: [number, number][] = [];
  for (let m = 0; m < 12; m++) if (months[m] && !months[(m + 11) % 12]) { let e = m; while (months[(e + 1) % 12] && (e + 1) % 12 !== m) e = (e + 1) % 12; runs.push([m, e]); }
  if (!runs.length) return 'bare all year';
  return runs.map(([a, e]) => (a === e ? MONTHS[a] : `${MONTHS[a]} to ${MONTHS[e]}`)).join(' and ');
}
