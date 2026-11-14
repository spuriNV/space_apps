import { EXTRAS, Num, PRIORITIES, Strategy, mmAf, r0 } from '../data';

export type Weather = 'typical' | '2022' | '2023';
export const WEATHER_LABEL: Record<Weather, string> = { typical: 'Typical year (2015–2025 average)', '2022': 'Replay 2022 drought', '2023': 'Replay 2023 storms' };

export interface Metric {
  key: string; label: string; unit: string; higherIsBetter: boolean;
  get: (s: Strategy, w: Weather) => Num;
  fmt: (n: number) => string;
  /** gain / give-up phrase for a difference d = alt - today (already signed in the "good" direction) */
  gain: string; loss: string; real: boolean;
}

const pick = (s: Strategy, w: Weather, typical: Num, k: 'irrigation_need_mm' | 'exposed_rain_days' | 'exposed_heat_days') => (w === 'typical' ? typical : s.replay[w][k]);

export const UNIT_METRICS: Metric[] = [
  {
    key: 'water', label: 'Irrigation water needed', unit: 'mm/yr', higherIsBetter: false, real: true,
    get: (s, w) => pick(s, w, s.water.irrigation_need_mm, 'irrigation_need_mm'),
    fmt: (n) => `${r0(n)} mm (${mmAf(n)})`, gain: 'Needs less irrigation water', loss: 'Needs more irrigation water',
  },
  {
    key: 'bare', label: 'Days the field sits bare', unit: 'days/yr', higherIsBetter: false, real: true,
    get: (s) => s.exposure.bare_days_per_year,
    fmt: (n) => `${r0(n)} days a year`, gain: 'Field bare fewer days', loss: 'Field bare more days',
  },
  {
    key: 'rain', label: 'Heavy rain on bare soil', unit: 'days/yr', higherIsBetter: false, real: true,
    get: (s, w) => pick(s, w, s.exposure.exposed_rain_days, 'exposed_rain_days'),
    fmt: (n) => `${n.toFixed(1)} days a year`, gain: 'Less heavy rain on bare soil', loss: 'More heavy rain on bare soil',
  },
  {
    key: 'heat', label: 'Hot days on bare soil (≥ 35 °C / 95 °F)', unit: 'days/yr', higherIsBetter: false, real: true,
    get: (s, w) => pick(s, w, s.exposure.exposed_heat_days, 'exposed_heat_days'),
    fmt: (n) => `${n.toFixed(0)} days a year`, gain: 'Fewer hot days on bare soil', loss: 'More hot days on bare soil',
  },
];

const scoreMetric = (p: { key: string; label: string; plain: string }): Metric => ({
  key: p.key, label: p.label, unit: 'score', higherIsBetter: true, real: false,
  get: (s) => s.scores[p.key], fmt: (n) => `${r0(n)} / 100`,
  gain: `${p.label}: better`, loss: `${p.label}: worse`,
});
export const SCORE_METRICS = PRIORITIES.map(scoreMetric);
export const EXTRA_METRICS = EXTRAS.map(scoreMetric);

export const span = (n: Num): [number, number] => [n.lo ?? n.v ?? 0, n.hi ?? n.v ?? 0];
export const rangeText = (n: Num, fmt: (x: number) => string = (x) => r0(x)) =>
  n.v == null ? 'not scored yet' : n.lo != null && n.hi != null && Math.round(n.lo) !== Math.round(n.hi) ? `${fmt(n.v)}, likely ${r0(n.lo)}–${r0(n.hi)}` : fmt(n.v);
