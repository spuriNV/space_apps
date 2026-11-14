// Single data-access seam (CONTRACT.md).
// Order per part: FastAPI route (http://localhost:8000) -> repo output file through the dev-server bridge (/repo/...,
// only for outputs the API has no route for yet; see README "API routes still needed") -> bundled mock (src/mock).
// If /api/health does not answer, everything comes from the bundled mocks and the UI says "Example data".
import type { Story, BCInfo, Calendar, CalendarYear, CellGrid, CoverClass, Dataset, GridLayer, Location, NewsItem, Regional, RotationStrategy, SourcedNumber, Source, ScoreKey } from './types';
import mockLocations from './mock/locations.json';
import mockCells from './mock/cells.json';
import mockCalendar from './mock/calendar.json';
import regional from './mock/regional.json';
import mockStrategies from './mock/strategies.json';
import mockNews from './mock/news.json';
import datasets from './mock/datasets.json';
import bc from './mock/bc.json';
import story from './mock/story.json';
import { YEARS } from './lib';

export const API = 'http://localhost:8000';
type ById<T> = Record<string, T>;

// ---------- provenance ----------
/** api = FastAPI real output; file = real repo output read via the dev bridge (no API route yet); mock = illustrative */
export type Origin = 'api' | 'file' | 'mock';
export interface Prov { part: string; label: string; origin: Origin; detail: string }
export type ProvMap = Record<string, Prov>;
const P = (part: string, label: string, origin: Origin, detail: string): Prov => ({ part, label, origin, detail });
export const isMock = (p?: Prov) => !p || p.origin === 'mock';

// ---------- fetch helpers ----------
async function getJSON(url: string, init?: RequestInit, ms = 15000) {
  const ctl = new AbortController();
  const h = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { ...init, signal: ctl.signal });
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return await r.json();
  } finally { clearTimeout(h); }
}
let health: Promise<boolean> | null = null;
/** true when the FastAPI app answers. Cached for the session. */
export const apiLive = () => (health ??= getJSON(`${API}/api/health`, undefined, 20000).then((b) => !!b?.ok).catch(() => false));
const file = (path: string) => getJSON(`/repo/${path}`);
/** API route if it serves real data (`_source: real`), else null */
async function apiReal(route: string, init?: RequestInit) {
  if (!(await apiLive())) return null;
  try { const b = await getJSON(`${API}${route}`, init); return b?._source === 'real' ? b : null; } catch { return null; }
}

// ---------- static / editorial ----------
export const getDatasets = () => Promise.resolve(datasets as Dataset[]);
export const getBC = () => Promise.resolve(bc as BCInfo);
export const getStory = (id: string) => Promise.resolve((story as unknown as ById<Story>)[id]);

// ---------- locations: mock card text + real outline, area, soil, crop history ----------
const KINGS = { short_name: 'Kings County forage', name: 'Kings County forage field for dairy (example)' };
const COUNTY: Record<string, string> = { '011': 'Colusa', '031': 'Kings' };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function realLocation(base: Location, live: boolean, apiLoc?: any): Promise<{ loc: Location; prov: ProvMap }> {
  const id = base.id;
  const prov: ProvMap = {
    outline: P('outline', 'Field outline', 'mock', 'placeholder square'),
    soil: P('soil', 'Soil (SSURGO)', 'mock', 'illustrative'),
    crop_history: P('crop_history', 'Crop on record (CDL)', 'mock', 'illustrative'),
    water: P('water', 'Water source, district, stations', 'mock', 'spec B1 text, unverified'),
  };
  if (!live) return { loc: base, prov };
  let loc: Location = { ...base, ...(id === 'caf_tulare_forage' ? KINGS : {}) };
  const [poly, soil, hist] = await Promise.all([
    file(`backend/field/polygons/${id}.geojson`).catch(() => null),
    file(`data/cache/${id}/soil.json`).catch(() => null),
    file(`backend/field/out/${id}/crop_history.json`).catch(() => null),
  ]);
  if (poly?.features?.[0]) {
    const f = poly.features[0], pr = f.properties, bs = pr.boundary_source ?? {};
    loc = { ...loc, geometry: f.geometry, centroid: pr.centroid,
      area_ha: { value: pr.area_ha, low: null, high: null, unit: 'ha', method: 'computed', source: { id: bs.id, title: bs.title, url: bs.url, verified: !!bs.verified }, note: 'area of the DWR outline in EPSG:32610' },
      county: bs.dwr_attributes?.COUNTY, dwr_id: bs.dwr_unique_id, boundary_title: bs.title };
    prov.outline = P('outline', 'Field outline', 'file', `DWR/Land IQ 2023 field ${bs.dwr_unique_id ?? ''}`.trim());
  }
  if (soil?.muname) {
    loc = { ...loc, soil: { muname: soil.muname, drainage_class: soil.drainage_class, hydrologic_group: soil.hydrologic_group, texture_class: soil.texture_class, awc_mm_per_m: soil.awc_mm_per_m, om_pct: soil.om_pct, ec_ds_per_m: soil.ec_ds_per_m, texture_detail: soil.texture_detail } };
    prov.soil = P('soil', 'Soil (SSURGO)', 'file', soil.muname);
  }
  if (hist?.by_year) {
    loc = { ...loc, crop_history: hist.by_year, cdl_source: hist.source };
    prov.crop_history = P('crop_history', 'Crop on record (CDL)', 'file', `USDA CDL ${Object.keys(hist.by_year)[0]}–${Object.keys(hist.by_year).slice(-1)[0]}`);
  }
  // GET /api/locations (real since build_real.py): outline, area, soil, crop history win over the files when present.
  // Water, events, card text stay from the bundled copy (the API also marks them as spec statements, U).
  if (apiLoc?.geometry) {
    const a = apiLoc;
    loc = { ...loc, geometry: a.geometry, centroid: a.centroid, area_ha: a.area_ha, county: COUNTY[a.county_fips] ?? loc.county,
      soil: { ...loc.soil, ...a.soil }, crop_history: a.crop_history ?? loc.crop_history };
    const tag = (k: string, label: string, d: string) => (prov[k] = P(k, label, 'api', d));
    tag('outline', 'Field outline', `DWR/Land IQ 2023${loc.dwr_id ? ` field ${loc.dwr_id}` : ''}`);
    if (a.soil?.muname) tag('soil', 'Soil (SSURGO)', a.soil.muname);
    if (a.crop_history) tag('crop_history', 'Crop on record (CDL)', 'USDA CDL 2008–2025');
  }
  return { loc, prov };
}
export async function getLocations(): Promise<{ locations: Location[]; prov: ById<ProvMap>; live: boolean }> {
  const live = await apiLive();
  const real = live ? await apiReal('/api/locations') : null;
  const byId = Object.fromEntries(((real?.items ?? []) as { id: string }[]).map((x) => [x.id, x]));
  const out = await Promise.all((mockLocations as unknown as Location[]).map((l) => realLocation(l, live, byId[l.id])));
  return { locations: out.map((o) => o.loc), prov: Object.fromEntries(out.map((o) => [o.loc.id, o.prov])), live };
}

// ---------- satellite calendar (backend/field/out/<id>/calendar.json) -> 10-day steps ----------
const CLS: Record<string, CoverClass> = { bare: 'b', partial: 'p', covered: 'c', water: 'w', unknown: 'u' };
const doy = (y: number, m: number, d: number) => Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 0)) / 864e5);
const dekadDate = (y: number, k: number) => [y, Math.floor(k / 3) + 1, [5, 15, 25][k % 3]] as const;
interface RealCalYear { year: number; segments: { start_doy: number; end_doy: number; class: string }[]; markers: { date: string; type: string }[]; observations: { date: string; ndvi: number | null; class: string }[] }
function convertCalendar(real: { years: RealCalYear[] }, mock: Calendar, hist: Record<string, string>): Calendar {
  const years: CalendarYear[] = YEARS.map((year, yi) => {
    const ry = real.years.find((y) => y.year === year);
    const my = mock.years[yi];
    if (!ry) return my;
    const obs = ry.observations.filter((o) => o.ndvi != null).map((o) => ({ t: Date.parse(o.date), v: o.ndvi as number }));
    let rule = '';
    const ndvi: number[] = [];
    for (let k = 0; k < 36; k++) {
      const [y, m, d] = dekadDate(year, k), q = doy(y, m, d), tt = Date.UTC(y, m - 1, d);
      const seg = ry.segments.find((s) => q >= s.start_doy && q <= s.end_doy);
      rule += CLS[seg?.class ?? 'unknown'] ?? 'u';
      const i = obs.findIndex((o) => o.t >= tt);
      const a = obs[i - 1], b = obs[i];
      ndvi.push(a && b && b.t - a.t <= 30 * 864e5 ? a.v + ((b.v - a.v) * (tt - a.t)) / (b.t - a.t || 1) : (b ?? a)?.v ?? 0);
    }
    const dk = (iso?: string) => { if (!iso) return null; const [, m, d] = iso.split('-').map(Number); return (m - 1) * 3 + (d <= 10 ? 0 : d <= 20 ? 1 : 2); };
    const up = ry.markers.find((m) => m.type === 'green_up' && m.date.startsWith(String(year)));
    const dn = ry.markers.find((m) => m.type === 'senescence_harvest' && m.date.startsWith(String(year)) && (!up || m.date > up.date));
    // ML detector output does not exist yet: ml mirrors the rule. ET and risk ticks stay illustrative (mock).
    return { ...my, year, cdl: hist[year] ?? my.cdl, rule, ml: rule, ndvi, greenup_dekad: dk(up?.date), senescence_dekad: dk(dn?.date) };
  });
  return { ...mock, years, real: true };
}

// ---------- 30 m grid (backend/field/out/<id>/grid.geojson) ----------
interface RealCell { type: 'Feature'; geometry: { type: 'Polygon'; coordinates: number[][][] }; properties: Record<string, number | string | null> }
function convertGrid(g: { layers: GridLayer[]; features: RealCell[] }): CellGrid {
  const keys = g.layers.map((l) => l.key);
  const feats = g.features.filter((f) => (f.properties.area_m2 as number) >= 150 && f.geometry.type === 'Polygon');
  const means = feats.map((f) => { const v = keys.map((k) => f.properties[k] as number | null).filter((x): x is number => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0; });
  const mu = means.reduce((a, b) => a + b, 0) / (means.length || 1);
  const sd = Math.sqrt(means.reduce((a, b) => a + (b - mu) ** 2, 0) / (means.length || 1)) || 1;
  const rows = Math.max(...feats.map((f) => f.properties.row as number)) + 1, cols = Math.max(...feats.map((f) => f.properties.col as number)) + 1;
  return {
    type: 'FeatureCollection', cell_m: 30, rows, cols, layers: g.layers,
    features: feats.map((f, i) => ({ type: 'Feature', geometry: f.geometry, properties: {
      id: i, r: f.properties.row as number, c: f.properties.col as number,
      v: Math.max(-1, Math.min(1, (means[i] - mu) / (2 * sd))), low: 0.5, edge: (f.properties.frac_in_field as number) < 0.9,
      nd: Object.fromEntries(keys.map((k) => [k, f.properties[k] as number | null])),
    } })),
  };
}

// ---------- strategies (API, engine output) -> the shape the B components read ----------
const CROP_LABEL: Record<string, string> = { open_water_flood: 'flood', rice_medium_grain: 'rice', cereal_vetch_cover: 'cereal + vetch cover', safflower: 'safflower', winter_wheat: 'winter wheat', alfalfa_hay: 'alfalfa', small_grain_silage: 'small-grain silage', silage_corn: 'silage corn', sorghum_sudan: 'sorghum-sudan' };
const md = (s: string) => { const [m, d] = s.split('-').map(Number); return m + (d - 1) / 31; };
function monthStrip(cal: { year: number; crop_id: string; plant: string; harvest: string; role: string }[], year: number) {
  const months: string[] = [], cover: string[] = [];
  for (let m = 1; m <= 12; m++) {
    const x = m + 0.5;
    const hit = cal.filter((c) => c.year === year).find((c) => { const a = md(c.plant), b = md(c.harvest); return a === b ? true : a < b ? x >= a && x < b : x >= a || x < b; });
    months.push(hit ? CROP_LABEL[hit.crop_id] ?? hit.crop_id.replace(/_/g, ' ') : 'bare');
    cover.push(!hit ? 'b' : hit.role === 'water' ? 'w' : hit.role === 'establishing' || (Math.abs(x - md(hit.plant)) < 1 && md(hit.plant) !== md(hit.harvest)) ? 'p' : 'c');
  }
  return { months, cover: cover.join('') };
}
const SHORT: Record<string, string> = { car0_rice_winterflood: 'Rice + winter flood', car1_rice_wintercover: 'Rice + winter cover', car2_dryyear_safflower: 'Dry-year safflower', car3_rice_wheat: 'Rice – wheat', caf0_alfalfa: 'Alfalfa stand', caf1_smallgrain_corn: 'Small grain + corn', caf2_smallgrain_sorghumsudan: 'Small grain + sorghum-sudan', caf3_alfalfa_break: 'Short alfalfa + break' };
const STRIP_YEAR: Record<string, number> = { caf3_alfalfa_break: 3 }; // show the break year
const blank = (unit: string, note: string, src?: Source): SourcedNumber => ({ value: 0, low: 0, high: 0, unit, method: 'lookup', note, source: src, blocked: true });
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normStrategy(s: any): RotationStrategy {
  const year = STRIP_YEAR[s.id] ?? 1;
  const strip = monthStrip(s.calendar, year);
  const rep = (y: string) => ({ irrigation_need_mm: s.exposure.replay?.[y]?.irrigation_need_mm ?? s.water.irrigation_need_mm, exposed_rain_days: s.exposure.replay?.[y]?.exposed_rain_days ?? s.exposure.exposed_rain_days, note: s.exposure.replay?.[y] ? `Engine replay of ${y} weather (NASA POWER)` : 'No replay for this year' });
  const rp = s.risk_profile;
  const r = (k: string) => (rp[k]?.value == null ? blank('share', rp[k]?.note ?? 'blocked', rp[k]?.source) : rp[k]);
  return {
    ...s,
    short_name: SHORT[s.id] ?? s.name.split(/[,(]/)[0].trim(),
    calendar_months: strip.months, month_cover: strip.cover, strip_year: year,
    exposure: { ...s.exposure, cover_basis: s.exposure.bare_days_per_year?.note ?? 'modelled from the calendar', replay: { 2022: rep('2022'), 2023: rep('2023') } },
    water: { ...s.water, etc_by_month_mm: (s.water.etc_by_month_mm ?? []).map((m: SourcedNumber | number) => (typeof m === 'number' ? m : m.value)),
      openet_et_mm_season: s.water.openet_et_mm_season?.value == null ? null : s.water.openet_et_mm_season, etc_vs_openet_pct: s.water.etc_vs_openet_pct?.value == null ? null : s.water.etc_vs_openet_pct },
    risk_profile: { ...rp, rma_share_drought: r('rma_share_drought'), rma_share_excess_moisture: r('rma_share_excess_moisture'), rma_share_heat: r('rma_share_heat'), crop: rp.crop ?? '', blocked: rp.rma_share_drought?.value == null },
    funding: (s.funding ?? []).filter((f: { applies?: boolean }) => f.applies !== false),
    brief: { why: [], evidence: [], local_review: [], gaps: [], ...s.brief },
  };
}
const mockStrats = (id: string) => (mockStrategies as unknown as RotationStrategy[]).filter((s) => s.location_id === id);

/** POST /api/locations/{id}/score: allocation in acre-ft/acre; returns null if the API is down */
export async function scoreStrategies(id: string, allocation: number, weights?: Partial<Record<ScoreKey, number>>) {
  const b = await apiReal(`/api/locations/${id}/score`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ allocation, ...(weights ? { weights } : {}) }) });
  return b?.items ? (b.items as unknown[]).map(normStrategy) : null;
}

// ---------- news ----------
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const normNews = (n: any): NewsItem => ({ ...n, verified: !!n.url && !n.url.includes('news.google.com'), signal: { label: n.signal?.dataset ?? '', value_pct: null, lead_days: null, ...n.signal } });

// ---------- everything the field view needs ----------
export interface FieldBundle { id: string; cells: CellGrid; cal: Calendar; regional: Regional; strategies: RotationStrategy[]; news: NewsItem[]; story: Story; prov: ProvMap }
export async function getField(loc: Location, live: boolean): Promise<FieldBundle> {
  const id = loc.id;
  const mCal = (mockCalendar as unknown as ById<Calendar>)[id];
  const prov: ProvMap = {
    calendar: P('calendar', 'Bare / covered / water calendar', 'mock', 'illustrative'),
    grid: P('grid', '30 m surface cells (3D top layer)', 'mock', 'illustrative'),
    strategies: P('strategies', 'Rotations and scores', 'mock', 'illustrative'),
    news: P('news', 'News headlines', 'mock', 'spec examples'),
    regional: P('regional', 'SMAP / GRACE slabs, trends', 'mock', 'no real trends route yet'),
    et: P('et', 'Crop water use (ET) and risk ticks', 'mock', 'OpenET needs a key; risk days not routed'),
    ml: P('ml', 'ML detector', 'mock', live ? 'not trained yet: toggle shows the rule' : 'illustrative'),
  };
  const base = { id, regional: (regional as unknown as ById<Regional>)[id], story: (story as unknown as ById<Story>)[id] };
  if (!live) return { ...base, cells: (mockCells as unknown as ById<CellGrid>)[id], cal: mCal, strategies: mockStrats(id), news: (mockNews as unknown as ById<NewsItem[]>)[id], prov };
  const [cal, grid, strat, news] = await Promise.all([
    apiReal(`/api/locations/${id}/calendar`).then((b) => b ?? file(`backend/field/out/${id}/calendar.json`).then((x) => ({ ...x, _via: 'file' }))).catch(() => null),
    apiReal(`/api/locations/${id}/grid`).then((b) => b ?? file(`backend/field/out/${id}/grid.geojson`).then((x) => ({ ...x, _via: 'file' }))).catch(() => null),
    apiReal(`/api/locations/${id}/strategies`),
    apiReal(`/api/locations/${id}/news`),
  ]);
  let c = mCal, cells = (mockCells as unknown as ById<CellGrid>)[id], strategies = mockStrats(id), nws = (mockNews as unknown as ById<NewsItem[]>)[id];
  if (cal?.years) { c = convertCalendar(cal, mCal, loc.crop_history); prov.calendar = P('calendar', 'Bare / covered / water calendar', cal._via === 'file' ? 'file' : 'api', 'Sentinel-2 + Landsat, NDVI rule'); }
  if (grid?.features) { cells = convertGrid(grid); prov.grid = P('grid', '30 m surface cells (3D top layer)', grid._via === 'file' ? 'file' : 'api', `${cells.features.length} cells · Sentinel-2 NDVI`); }
  if (strat?.items?.length) { strategies = strat.items.map(normStrategy); prov.strategies = P('strategies', 'Rotations and scores', 'api', 'rotation engine'); }
  if (news?.items?.length) { nws = news.items.map(normNews); prov.news = P('news', 'News headlines', 'api', `${news.items.length} cached headlines`); }
  return { ...base, cells, cal: c, strategies, news: nws, prov };
}
