import type { CellProps } from './types';

export type MeasureKey = 'ndvi' | 'et' | 'stress';
export interface Measure { key: MeasureKey; label: string; long: string; prop: keyof CellProps; unit: string; domain: [number, number]; stops: [number, string][]; lowLabel: string; highLabel: string; source: string; fmt: (v: number) => string }

export const MEASURES: Record<MeasureKey, Measure> = {
  ndvi: {
    key: 'ndvi', label: 'Cover', long: 'Plant cover (NDVI)', prop: 'ndvi', unit: 'NDVI', domain: [0.15, 0.9],
    stops: [[0.15, '#9c6b3f'], [0.35, '#dcc27a'], [0.5, '#cfe07a'], [0.7, '#5fb55a'], [0.9, '#1b7a3a']],
    lowLabel: 'bare', highLabel: 'dense cover', source: 'HLS 30 m', fmt: (v) => v.toFixed(2),
  },
  et: {
    key: 'et', label: 'Water use', long: 'Water use (ET)', prop: 'et_mm_day', unit: 'mm/day', domain: [2, 7.6],
    stops: [[2, '#eef3fb'], [3.5, '#b7d3ee'], [5, '#6aa6dd'], [6.3, '#2a72c4'], [7.6, '#0b3f8f']],
    lowLabel: 'low', highLabel: 'high', source: 'OpenET 30 m', fmt: (v) => v.toFixed(1),
  },
  stress: {
    key: 'stress', label: 'Heat stress', long: 'Heat vs field median', prop: 'lst_anom_k', unit: 'K', domain: [-2.5, 6],
    stops: [[-2.5, '#fff7c9'], [0, '#fedc86'], [2, '#fb9a3c'], [4, '#e4501f'], [6, '#a80f1e']],
    lowLabel: 'cooler', highLabel: 'hotter', source: 'ECOSTRESS 70 m, resampled', fmt: (v) => (v > 0 ? '+' : '') + v.toFixed(1),
  },
};

export function colorFor(m: Measure, v: number): string {
  const s = m.stops;
  if (v <= s[0][0]) return s[0][1];
  for (let i = 1; i < s.length; i++) {
    if (v <= s[i][0]) {
      const t = (v - s[i - 1][0]) / (s[i][0] - s[i - 1][0]);
      const a = parseInt(s[i - 1][1].slice(1), 16), b = parseInt(s[i][1].slice(1), 16);
      const ch = (sh: number) => Math.round(((a >> sh) & 255) + t * (((b >> sh) & 255) - ((a >> sh) & 255)));
      return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
    }
  }
  return s[s.length - 1][1];
}
export const gradientCss = (m: Measure) => `linear-gradient(90deg, ${m.stops.map(([v, c]) => `${c} ${(((v - m.domain[0]) / (m.domain[1] - m.domain[0])) * 100).toFixed(0)}%`).join(', ')})`;
