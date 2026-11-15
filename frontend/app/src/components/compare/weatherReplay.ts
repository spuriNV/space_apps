// Dry / wet / typical year: irrigation need from engine replay (2022, 2023) or 2015–2025 mean.
import type { RotationStrategy } from '../../types';
import { isBC } from '../../api';
import { t } from '../../i18n';
import type { Location } from '../../types';
import { isRainFed, mmToAfac } from '../../lib';

export type Weather = 'typical' | '2022' | '2023';

export const WEATHER_LABEL: Record<Weather, string> = {
  typical: t('compare.wTypical'),
  '2022': t('compare.wDry'),
  '2023': t('compare.wWet'),
};

export function weatherLabels(loc: Location): Record<Weather, string> {
  if (!isBC(loc)) return WEATHER_LABEL;
  return { typical: t('compare.wTypical'), '2022': t('compare.bcDry'), '2023': t('compare.bcWet') };
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
    return t('compare.blTypical', { n: typ.toFixed(1) });
  }

  const headline = w === '2022'
    ? (bc ? t('compare.bl2022bc') : t('compare.bl2022'))
    : (bc ? t('compare.bl2023bc') : t('compare.bl2023'));

  const d = cur - typ;
  let needLine: string;
  if (Math.abs(d) < 0.08) {
    needLine = t('compare.needSame', { n: cur.toFixed(1), d: Math.abs(d).toFixed(1) });
  } else if (d > 0) {
    needLine = t('compare.needMore', { n: cur.toFixed(1), d: d.toFixed(1), typ: typ.toFixed(1) });
  } else {
    needLine = t('compare.needLess', { n: cur.toFixed(1), d: (-d).toFixed(1), typ: typ.toFixed(1) });
  }

  const rain = exposedRainDays(rotation, w);
  const rainTyp = rotation.exposure.exposed_rain_days;
  const rainBit = rain.value != null && Math.abs((rain.value ?? 0) - (rainTyp.value ?? 0)) >= 0.4
    ? ` ${t('compare.heavyRainBit', { n: rain.value!.toFixed(1), y: w === '2022' ? t('compare.dryYearP') : t('compare.wetYearP') })}`
    : '';

  return `${headline} ${needLine}${rainBit}${dataNote ? ` ${dataNote}` : ''}`;
}

export function fitsLimit(s: RotationStrategy, w: Weather, allocation: number): string {
  const need = waterOf(s, w);
  if (need.rf) return t('compare.fitsLimit');
  if (need.v == null) return t('compare.needNotScored');
  if ((need.hi ?? 0) <= allocation) return t('compare.fitsLimit');
  if ((need.lo ?? 0) > allocation) return t('compare.overLimit');
  return t('compare.mayGoOver');
}