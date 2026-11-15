// Dry / wet / typical year: irrigation need from engine replay (2022, 2023) or 2015–2025 mean.
import type { RotationStrategy } from '../../types';
import { isBC } from '../../api';
import type { Location } from '../../types';
import { isRainFed, mmToAfac } from '../../lib';

export type Weather = 'typical' | '2022' | '2023';

export const WEATHER_LABEL: Record<Weather, string> = {
  typical: 'Typical year',
  '2022': 'Dry, like 2022',
  '2023': 'Wet, like 2023',
};

export function weatherLabels(loc: Location): Record<Weather, string> {
  if (!isBC(loc)) return WEATHER_LABEL;
  return { typical: 'Typical year', '2022': 'Drier year (2022 weather)', '2023': 'Restricted water (like 2023)' };
}

export function irrigationNeedMm(s: RotationStrategy, w: Weather) {
  if (w === 'typical') return s.water.irrigation_need_mm;
  const r = s.exposure.replay?.[w]?.irrigation_need_mm;
  return r ?? s.water.irrigation_need_mm;
}

export function exposedRainDays(s: RotationStrategy, w: Weather) {
  if (w === 'typical') return s.exposure.exposed_rain_days;
  return s.exposure.replay?.[w]?.exposed_rain_days ?? s.exposure.exposed_rain_days;
}

export interface WaterAf { v: number | null; lo: number | null; hi: number | null; rf?: boolean }

export function waterOf(s: RotationStrategy, w: Weather): WaterAf {
  if (isRainFed(s)) return { v: 0, lo: 0, hi: 0, rf: true };
  const n = irrigationNeedMm(s, w);
  if (n.value == null || n.blocked) return { v: null, lo: null, hi: null };
  return {
    v: mmToAfac(n.value),
    lo: mmToAfac(n.low ?? n.value),
    hi: mmToAfac(n.high ?? n.value),
  };
}

const TYPICAL_AF = (s: RotationStrategy) => mmToAfac(s.water.irrigation_need_mm.value);

/** Plain sentence when the grower picks a weather year (always visible on phone). */
export function scenarioBlurb(loc: Location, w: Weather, rotation: RotationStrategy): string {
  const bc = isBC(loc);
  const typ = TYPICAL_AF(rotation);
  const need = waterOf(rotation, w);
  const cur = need.v ?? typ;
  const replayNote = w !== 'typical' ? rotation.exposure.replay?.[w]?.note?.trim() : '';
  const dataNote = replayNote && !/^engine replay/i.test(replayNote) ? replayNote : '';

  if (w === 'typical') {
    return `Typical year uses average sun, rain and heat here, 2015–2025. This rotation needs about ${typ.toFixed(1)} acre-ft/acre of irrigation in the model.`;
  }

  const headline = w === '2022'
    ? (bc ? '2022 had less rain and tighter irrigation orders on many farms.' : 'Dry like 2022: less rain and more heat at this field.')
    : (bc ? '2023 brought a wet winter; many growers irrigated less.' : 'Wet like 2023: more winter rain and some cooler weeks.');

  const d = cur - typ;
  let needLine: string;
  if (Math.abs(d) < 0.08) {
    needLine = `In the model, irrigation need stays about ${cur.toFixed(1)} acre-ft/acre (within ${Math.abs(d).toFixed(1)} of a typical year). Most rain still falls before summer pumping.`;
  } else if (d > 0) {
    needLine = `Needs about ${cur.toFixed(1)} acre-ft/acre, roughly ${d.toFixed(1)} more than a typical year (${typ.toFixed(1)}).`;
  } else {
    needLine = `Needs about ${cur.toFixed(1)} acre-ft/acre, roughly ${(-d).toFixed(1)} less than a typical year (${typ.toFixed(1)}).`;
  }

  const rain = exposedRainDays(rotation, w);
  const rainTyp = rotation.exposure.exposed_rain_days;
  const rainBit = rain.value != null && Math.abs((rain.value ?? 0) - (rainTyp.value ?? 0)) >= 0.4
    ? ` Heavy rain on bare soil: about ${rain.value!.toFixed(1)} days a year${w === '2022' ? ' (dry year)' : ' (wet year)'}.`
    : '';

  return `${headline} ${needLine}${rainBit}${dataNote ? ` ${dataNote}` : ''}`;
}

export function fitsLimit(s: RotationStrategy, w: Weather, allocation: number): string {
  const need = waterOf(s, w);
  if (need.rf) return 'Fits your limit';
  if (need.v == null) return 'Need not scored yet';
  if ((need.hi ?? 0) <= allocation) return 'Fits your limit';
  if ((need.lo ?? 0) > allocation) return 'Over your limit';
  return 'May go over your limit';
}