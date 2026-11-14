// Single data-access layer (CONTRACT.md). Today: reads src/mock/*.json.
// Later: swap each function body for fetch(`${API}/api/...`) — routes are in planner-spec.md B3.
import locationsJson from './mock/locations.json';
import strategiesJson from './mock/strategies.json';
import cellsJson from './mock/cells.json';
import fieldYearJson from './mock/field-year.json';
import newsJson from './mock/news.json';
import sourcesJson from './mock/sources.json';
import type { BcCard, CellGrid, FieldYear, Location, NewsItem, PriorityKey, RotationStrategy, ScoredStrategy, Source, Weights } from './types';

export const IS_MOCK = true;
export const API = 'http://localhost:8000';

const locs = (locationsJson as unknown as { locations: Location[]; bc: BcCard });
const strategies = strategiesJson as unknown as RotationStrategy[];

/** GET /api/locations */
export const getLocations = (): Location[] => locs.locations;
/** GET /api/locations/{id} */
export const getLocation = (id: string): Location => locs.locations.find((l) => l.id === id)!;
/** GET /api/bc/signal (opener card only; BC is out of scope) */
export const getBcCard = (): BcCard => locs.bc;
/** GET /api/locations/{id}/strategies */
export const getStrategies = (id: string): RotationStrategy[] => strategies.filter((s) => s.location_id === id);
/** GET /api/locations/{id}/zones (30 m cells) */
export const getCells = (id: string): CellGrid => (cellsJson as unknown as Record<string, CellGrid>)[id];
/** GET /api/locations/{id}/features/weekly + /models */
export const getFieldYear = (id: string): FieldYear => (fieldYearJson as unknown as Record<string, FieldYear>)[id];
/** GET /api/locations/{id}/news */
export const getNews = (id: string): NewsItem[] => (newsJson as unknown as Record<string, NewsItem[]>)[id];
export const getSource = (id: string): Source => (sourcesJson as unknown as Record<string, Source>)[id];

export const PRIORITIES: { key: PriorityKey; label: string; hint: string }[] = [
  { key: 'water_use', label: 'Water use', hint: 'Less irrigation water per season scores higher' },
  { key: 'forage_value', label: 'Forage', hint: 'Feed produced for the herd' },
  { key: 'n_fixation', label: 'Nitrogen', hint: 'Nitrogen fixed by legumes' },
  { key: 'erosion', label: 'Erosion', hint: 'Fewer bare days exposed to heavy rain' },
  { key: 'organic_matter', label: 'Organic matter', hint: 'Residue, roots and soil building' },
  { key: 'market', label: 'Market', hint: 'Fit to your market and equipment' },
];
export const DEFAULT_WEIGHTS: Weights = { water_use: 1, forage_value: 1, n_fixation: 1, erosion: 1, organic_matter: 1, market: 1 };

/** POST /api/locations/{id}/score  {weights, ...}  (spec B4.12: composite = Σ W_i s_i with low/high; tie when intervals overlap > 50%) */
export function scoreStrategies(id: string, weights: Weights): ScoredStrategy[] {
  const total = PRIORITIES.reduce((a, p) => a + weights[p.key], 0) || 1;
  const scored = getStrategies(id).map((s) => {
    const sum = (k: 'value' | 'low' | 'high') => PRIORITIES.reduce((a, p) => a + weights[p.key] * (s.scores[p.key][k] ?? 0), 0) / total;
    return { ...s, composite: { value: Math.round(sum('value')), low: Math.round(sum('low')), high: Math.round(sum('high')), weights_used: weights }, rank: 0, tie: false, best: false };
  });
  const order = [...scored].sort((a, b) => b.composite.value - a.composite.value);
  const top = order[0];
  order.forEach((s, i) => {
    s.rank = i + 1;
    s.best = i === 0;
    if (i > 0) {
      const overlap = Math.min(s.composite.high, top.composite.high) - Math.max(s.composite.low, top.composite.low);
      const narrow = Math.max(1, Math.min(s.composite.high - s.composite.low, top.composite.high - top.composite.low));
      s.tie = overlap / narrow > 0.5;
    }
  });
  if (order.some((s) => s.tie)) top.tie = true;
  return scored;
}

// ---- unit helpers (dual units, spec B8) ----
export const MM_PER_AF_AC = 304.8;
export const mmToAfAc = (mm: number) => mm / MM_PER_AF_AC;
export const mmToIn = (mm: number) => mm / 25.4;
export const haToAc = (ha: number) => ha * 2.47105;
