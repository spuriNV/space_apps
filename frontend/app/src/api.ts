// Single data-access seam (CONTRACT.md).
// Everything real comes from the CropLytics API at VITE_API_BASE: http://localhost:8000/api in dev, same-origin /api in a
// production build (the backend serves the built app and the API from one origin). Anything the API does not answer falls
// back to the bundled examples in src/mock, and the UI says so in the source line.
import type { BCInfo, Calendar, CalendarYear, CellGrid, CoverClass, DataGap, Dataset, FirstNations, GridLayer, Location, NewsItem, Regional, RotationStrategy, SourcedNumber, Source, ScoreKey } from './types';
import mockLocations from './mock/locations.json';
import mockCells from './mock/cells.json';
import mockCalendar from './mock/calendar.json';
import regional from './mock/regional.json';
import mockStrategies from './mock/strategies.json';
import mockNews from './mock/news.json';
import datasets from './mock/datasets.json';
import bc from './mock/bc.json';
import fieldExtra from './mock/field_extra.json';
import { YEARS, dateToT } from './lib';
import type { Daily } from './season';
import outlookExample from './mock/outlook.example.json';
import { nasaList, type NasaDataset, type NasaStatus } from './nasa';

export const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api')).replace(/\/+$/, '');
const BASE = import.meta.env.BASE_URL ?? '/';
type ById<T> = Record<string, T>;

/** Example water limit per field, until the grower types their own (PLAN.md decisions, 14 Nov). acre-ft/acre */
export const EXAMPLE_LIMIT: Record<string, number> = { car_colusa_rice: 5.0, caf_tulare_forage: 3.0 };

// ---------- provenance ----------
/** api = real backend output from the API; estimate = the API's stand-in for data a region lacks (`_source: "estimate"`, BC);
 *  file = real output copied into the app (no route yet); mock = illustrative */
export type Origin = 'api' | 'estimate' | 'file' | 'mock';
export interface Prov { part: string; label: string; origin: Origin; detail: string }
export type ProvMap = Record<string, Prov>;
export const P = (part: string, label: string, origin: Origin, detail: string): Prov => ({ part, label, origin, detail });
export const isMock = (p?: Prov) => !p || p.origin === 'mock';
/** 'estimate' when the API filled a region gap with an estimate (`_source: "estimate"`), else 'api'. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const orig = (b: any): Origin => (b?._source === 'estimate' ? 'estimate' : 'api');
/** Real data, or the API's labelled estimate for a region gap (BC). Example files (`_source: "mock"`) are not. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const usable = (b: any) => b && (b._source === 'real' || b._source === 'estimate' || b._source === 'live' || b._source === 'catalog' || b._source === 'user' || b._source === undefined);

// ---------- fetch helpers ----------
async function getJSON(url: string, init?: RequestInit, ms = 20000) {
  const ctl = new AbortController();
  const h = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { ...init, signal: ctl.signal });
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return await r.json();
  } finally { clearTimeout(h); }
}
/** `route` is written as the API path (`/api/locations/...`); API_BASE replaces the `/api` prefix. */
const get = (route: string, init?: RequestInit, ms?: number) => getJSON(`${API_BASE}${route.replace(/^\/api/, '')}`, init, ms);
let health: Promise<boolean> | null = null;
/** true when the API answers. Cached for the session. */
export const apiLive = () => (health ??= get('/api/health').then((b) => !!b?.ok).catch(() => false));
/** The route's body if it is real data (`_source: real`, or no `_source` for routes that are real-only), else null. */
/** Like apiReal, but tells a route the API does not have for this field (404: not built yet) apart from one that failed. */
async function apiRealOr404(route: string): Promise<{ body: any; missing: boolean }> { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!(await apiLive())) return { body: null, missing: false };
  try {
    const r = await fetch(`${API_BASE}${route.replace(/^\/api/, '')}`);
    if (r.status === 404) return { body: null, missing: true };
    if (!r.ok) return { body: null, missing: false };
    const b = await r.json();
    return { body: usable(b) ? b : null, missing: false };
  } catch { return { body: null, missing: false }; }
}
const missing404 = new Set<string>(); // routes that answered 404 once: not asked again this session
async function apiReal(route: string, init?: RequestInit, ms = 12000) {
  if (missing404.has(route) || !(await apiLive())) return null;
  try { const b = await get(route, init, ms); return usable(b) ? b : null; } catch (e) { if (/^404 /.test(String((e as Error).message))) missing404.add(route); return null; }
}

// ---------- static / editorial ----------
/** GET /api/glossary (plain-language terms), only when the API serves real content. */
export async function getGlossary(): Promise<Record<string, { term: string; short: string }>> {
  const b = await apiReal('/api/glossary');
  return Object.fromEntries(((b?.items ?? []) as { id: string; term: string; short: string }[]).map((x) => [x.id, x]));
}
export const getDatasets = () => Promise.resolve(datasets as Dataset[]);
export const getBC = () => Promise.resolve(bc as BCInfo);

// ---------- regions (BC) ----------
export const isBC = (l?: Location | null) => l?.region === 'bc';
/** A BC field's data gap by id (`data_gaps` on the location route), or null for a California field. */
export const bcGap = (l: Location | null | undefined, id: string): DataGap | null => (isBC(l) ? l!.data_gaps?.find((g) => g.id === id) ?? null : null);
/** GET .../first_nations (BC only; California fields answer 404). */
export async function getFirstNations(id: string): Promise<FirstNations | null> {
  const b = await apiReal(`/api/locations/${id}/first_nations`);
  return b?.statement ? (b as FirstNations) : null;
}
/** GET .../first_nations/reserves.geojson: reserve outlines near a BC field, for context only. */
export async function getReserves(id: string): Promise<GeoJSON.FeatureCollection | null> {
  const b = await apiReal(`/api/locations/${id}/first_nations/reserves.geojson`, undefined, 20000);
  return b?.features ? (b as GeoJSON.FeatureCollection) : null;
}

// ---------- locations: bundled card text + the API's outline, area, soil, crop history ----------
const KINGS = { short_name: 'Kings County forage', name: 'Kings County forage field for dairy (example)' };
const COUNTY: Record<string, string> = { '011': 'Colusa', '031': 'Kings' };
const EXTRA = (fieldExtra as unknown as { fields: ById<{ rma?: Location['rma'] }> }).fields;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function realLocation(base: Location, apiLoc?: any): { loc: Location; prov: ProvMap } {
  const prov: ProvMap = {
    outline: P('outline', 'Field outline', 'mock', 'placeholder square'),
    soil: P('soil', 'Soil (USDA soil survey)', 'mock', 'illustrative'),
    crop_history: P('crop_history', 'Crop on record (USDA Cropland Data Layer)', 'mock', 'illustrative'),
    water: P('water', 'Water source and district', 'mock', 'project brief, not looked up'),
  };
  if (EXTRA[base.id]?.rma) prov.rma = P('rma', 'Crop-insurance payouts (USDA RMA)', 'file', 'backend/ground, 2010–2024');
  // example limit per field until the grower moves it: the API's own example (BC) when it sends one, else by crop family
  EXAMPLE_LIMIT[base.id] ??= apiLoc?.water?.example_limit_af_ac?.value ?? (/^car|rice/.test(base.id) || apiLoc?.family === 'rice' ? 5.0 : 3.0);
  let loc: Location = { ...base, rma: EXTRA[base.id]?.rma, water: { ...base.water, allocation_input: { unit: 'acre-ft/acre', value: EXAMPLE_LIMIT[base.id] } } };
  if (!apiLoc?.geometry) return { loc, prov };
  const a = apiLoc;
  loc = { ...loc, ...(base.id === 'caf_tulare_forage' ? KINGS : {}),
    geometry: a.geometry, centroid: a.centroid, area_ha: a.area_ha, county: a.county_name ?? COUNTY[a.county_fips] ?? loc.county,
    family: a.family ?? loc.family, farmer_name: a.farmer_name ?? loc.farmer_name, county_name: a.county_name ?? loc.county_name,
    dwr_id: a.dwr_unique_id ?? a.dwr_id,
    soil: { ...loc.soil, ...a.soil },
    crop_history: a.crop_history ?? loc.crop_history, nasa_datasets: a.nasa_datasets, datasets: a.datasets, terrain: a.terrain ?? loc.terrain,
    nasadem: a.terrain?.slope_mean_pct?.value != null ? { slope_mean_pct: a.terrain.slope_mean_pct.value, slope_p90_pct: a.terrain.slope_p90_pct?.value, low_spot_fraction: a.terrain.low_spot_fraction?.value } : undefined,
    region: a.region === 'bc' || a.region === 'other' ? a.region : 'ca', state_code: a.state_code ?? null, county_kind: a.county_kind, data_gaps: a.data_gaps, water_context: a.water_context, first_nations: a.first_nations };
  if (loc.nasadem) prov.terrain = P('terrain', 'Slope and low spots (NASADEM)', 'api', 'NASA JPL elevation, 30 m');
  // water district / GSA: use the API's only when it is looked up or verified (status from lookup / verified, not text markers); a looked-up field may have no district
  const w = a.water;
  if (w && (w.lookup || (w.district && w.verified === true)) && w.verified !== false) { loc = { ...loc, water: { ...loc.water, ...w, allocation_input: loc.water.allocation_input }, water_real: true }; prov.water = P('water', 'Water source and district', 'api', String(w.district ?? w.sgma_subbasin ?? 'looked up')); }
  if (loc.region === 'bc') {
    // BC: a ParcelMap BC parcel clipped to AAFC forage pixels; AAFC crop inventory; AAFC Soil Landscapes of Canada; no California water district
    prov.outline = P('outline', 'Field outline', 'api', 'ParcelMap BC parcel inside the farmland reserve, clipped to AAFC forage pixels');
    const slc = /aafc|slc/i.test(a.soil?.source?.id ?? a.soil?.awc_mm_per_m?.source?.id ?? '');
    prov.soil = P('soil', slc ? 'Soil (AAFC Soil Landscapes of Canada)' : 'Soil (SoilGrids global model)', 'api', a.soil?.mukey === 'pending' ? 'not fetched yet' : slc ? 'AAFC Soil Landscapes of Canada v3.2, 1:1,000,000' : 'ISRIC SoilGrids v2');
    if (a.crop_history) prov.crop_history = P('crop_history', 'Crop on record (AAFC Annual Crop Inventory)', 'api', 'AAFC ACI 2011–2025');
    prov.water = P('water', 'Watershed and irrigation orders', 'api', a.water_context?.watershed ?? 'BC Water Sustainability Act');
    loc = { ...loc, water: { ...loc.water, source: a.water?.source ?? null } }; // not the forage example's wells
    return { loc, prov };
  }
  prov.outline = P('outline', 'Field outline', 'api', `DWR / Land IQ 2023${loc.dwr_id ? ` field ${loc.dwr_id}` : ''}`);
  if (a.soil?.muname) prov.soil = P('soil', 'Soil (USDA soil survey)', 'api', a.soil.muname);
  if (a.crop_history) prov.crop_history = P('crop_history', 'Crop on record (USDA Cropland Data Layer)', 'api', 'USDA CDL 2008–2025');
  return { loc, prov };
}
/** The bundled example field a new field borrows its example numbers from (rice or forage). */
const MOCK_IDS = new Set((mockLocations as unknown as Location[]).map((l) => l.id));
export const templateId = (id: string, family?: string) => (MOCK_IDS.has(id) ? id : family === 'rice' || id.startsWith('car') ? 'car_colusa_rice' : 'caf_tulare_forage');
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function baseFor(item: any): Location {
  const mocks = mockLocations as unknown as Location[];
  const m = mocks.find((l) => l.id === item.id);
  if (m) return m;
  const t = mocks.find((l) => l.id === templateId(item.id, item.family))!;
  // a new field: only the shape comes from the example; its own values come from the API (no example soil or water leaks in)
  return { ...t, id: item.id, name: item.farmer_name ?? item.name ?? item.id, short_name: item.farmer_name ?? item.id, headline: '', events: item.events ?? [], stations: item.stations ?? [],
    observed_cover: item.observed_cover ?? { summary: '' }, crop_history: item.crop_history ?? {}, market_preference: item.market_preference ?? t.market_preference,
    soil: {} as Location['soil'], terrain: item.terrain ?? t.terrain, county: item.county_name, water: { ...t.water, district: '', sgma_subbasin: '', sgma_status: { text: '', url: '', verified: false } } };
}
export async function getLocations(): Promise<{ locations: Location[]; prov: ById<ProvMap>; live: boolean }> {
  const live = await apiLive();
  const real = live ? await apiReal('/api/locations') : null;
  // the BC field, when the API serves it but the default list leaves it out (pre-merge APIs have no region at all)
  if (real?.items && real.facets?.region?.bc && !real.items.some((x: { region?: string }) => x.region === 'bc')) {
    const bcList = await apiReal('/api/locations?region=bc');
    if (bcList?.items?.length) real.items = [...real.items, ...bcList.items];
  }
  // every field the API serves (the bundled two when it does not answer)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const items: any[] = real?.items?.length ? real.items : (mockLocations as unknown as Location[]).map((l) => ({ id: l.id }));
  // the list route may omit newer per-field keys (nasa_datasets); the single-field route carries them
  const one = live ? await Promise.all(items.map((x) => (x.geometry && x.nasa_datasets ? x : apiReal(`/api/locations/${x.id}`)))) : [];
  const out = items.map((x, i) => realLocation(baseFor(one[i] ?? x), one[i]?.geometry ? one[i] : x.geometry ? x : undefined));
  return { locations: out.map((o) => o.loc), prov: Object.fromEntries(out.map((o) => [o.loc.id, o.prov])), live: live && !!real };
}

// ---------- a spot tapped on the map (GET /api/analyze) ----------
/** Tapped spots have `pt_` ids. Only /locations/{pid}, /strategies, /daily (NASA POWER columns) and POST /score answer for them. */
export const isSpot = (id?: string | null) => !!id && id.startsWith('pt_');
/** A field the user drew (`my_` id, or the `my_draft` stand-in while it is saved): src/myFields.ts. */
export const isMine = (id?: string | null) => !!id && id.startsWith('my_');
/** Ids that answer only /locations/{id}, /strategies, /daily and POST /score: tapped spots and drawn fields. */
export const isLite = (id?: string | null) => isSpot(id) || isMine(id);
const MOCK_LOCS = mockLocations as unknown as Location[];
const haversineKm = (lat1: number, lon1: number, lat2: number, lon2: number) => {
  const r = 6371, p = Math.PI / 180, dLat = (lat2 - lat1) * p, dLon = (lon2 - lon1) * p;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * p) * Math.cos(lat2 * p) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
};
/** Nearest prepared California field: borrow regional NASA series and 30 m grid when pt_/my_ has no own routes yet. */
export function nearestCaPreset(loc: Location, presets: Location[] = MOCK_LOCS): string {
  let best = templateId(loc.id, loc.family), bestKm = 1e99;
  for (const p of presets) {
    if (isLite(p.id) || p.region === 'bc' || !p.centroid) continue;
    const km = haversineKm(loc.centroid.lat, loc.centroid.lon, p.centroid.lat, p.centroid.lon);
    if (km < bestKm) { bestKm = km; best = p.id; }
  }
  return best;
}
function presetCentroid(presetId: string, presets: Location[]): Location['centroid'] | null {
  return presets.find((p) => p.id === presetId)?.centroid ?? MOCK_LOCS.find((p) => p.id === presetId)?.centroid ?? null;
}
function shiftGrid(g: CellGrid, dLon: number, dLat: number): CellGrid {
  const shiftPoly = (coords: number[][][]) => coords.map((ring) => ring.map(([x, y]) => [x + dLon, y + dLat]));
  return {
    ...g,
    features: g.features.map((f) => {
      const geom = f.geometry;
      if (geom.type !== 'Polygon') return f;
      return { ...f, geometry: { type: 'Polygon', coordinates: shiftPoly(geom.coordinates as number[][][]) } };
    }),
  };
}
function gridAt(loc: Location, presetId: string): CellGrid | null {
  const raw = (mockCells as unknown as ById<CellGrid>)[presetId];
  if (!raw) return null;
  const from = MOCK_LOCS.find((l) => l.id === presetId);
  if (!from) return raw;
  return shiftGrid(raw, loc.centroid.lon - from.centroid.lon, loc.centroid.lat - from.centroid.lat);
}
const calFor = (cal: Calendar, id: string) => ({ ...cal, location_id: id });
const gridCache = new Map<string, ReturnType<typeof apiReal>>();
const gridFetch = (id: string) => {
  let p = gridCache.get(id);
  if (!p) { p = apiReal(`/api/locations/${id}/grid`, undefined, 30000); gridCache.set(id, p); }
  return p;
};
/** Warm API caches for 3D stack (nearest preset grid + series). Safe to call while a spot is still analysing. */
export function prefetchFieldStack(loc: Location, caPresets?: Location[]) {
  if (!isLite(loc.id)) return;
  void apiLive().then((live) => {
    if (!live) return;
    const borrow = nearestCaPreset(loc, caPresets ?? MOCK_LOCS);
    gridFetch(borrow);
    void apiReal(`/api/locations/${borrow}/calendar`);
    void apiReal(`/api/locations/${borrow}/calendar?source=hls`);
    void apiReal(`/api/locations/${borrow}/nasa_series`);
    void apiReal(`/api/locations/${loc.id}/grid`, undefined, 30000);
  });
}
/** Immediate 3D stack from shifted mock grid + nearest preset calendar/regional (no network). */
export function fieldStackSeed(loc: Location, live: boolean, caPresets?: Location[]): FieldBundle {
  const id = loc.id, lite = isLite(id), presets = caPresets ?? MOCK_LOCS, borrow = lite ? nearestCaPreset(loc, presets) : id;
  const mid = templateId(id, loc.family);
  const mCal = padCalendar((mockCalendar as unknown as ById<Calendar>)[lite ? borrow : mid] ?? (mockCalendar as unknown as ById<Calendar>)[mid]);
  const reg0 = (regional as unknown as ById<Regional>)[lite ? borrow : mid];
  const prov: ProvMap = {
    calendar: P('calendar', 'Bare / green / flooded calendar', 'mock', lite ? `illustrative · nearest prepared field (${borrow})` : 'illustrative'),
    grid: P('grid', '100 ft squares in the 3D view', 'mock', lite ? `illustrative · shifted from ${borrow}` : 'illustrative'),
    strategies: P('strategies', 'Rotations, water need and scores', 'mock', 'still loading'),
    news: P('news', 'News headlines', 'mock', 'project brief examples'),
    regional: P('regional', 'Soil moisture (SMAP) and groundwater (GRACE-FO)', 'mock', lite ? `example numbers · nearest prepared field (${borrow})` : 'no real series served yet'),
    ml: P('ml', 'Machine-learning calendar', 'mock', 'not served'),
  };
  // Squares sit on this outline immediately (template grid shifted onto the field). /grid replaces them.
  const cells = gridAt(loc, lite ? borrow : mid) ?? gridAt(loc, 'car_colusa_rice');
  const used: Partial<Record<string, NasaStatus>> = loc.nasadem ? { nasadem: 'live' } : {};
  const nasa = () => nasaList(loc.nasa_datasets, loc.datasets, used).list;
  return {
    id, regional: reg0, cells, cal: calFor(mCal, id), strategies: lite ? [] : mockStrats(mid),
    news: lite ? [] : (mockNews as unknown as ById<NewsItem[]>)[mid], ml: null,
    nasa: nasa().map((d) => (live && d.status === 'live' && d.id !== 'iss' ? { ...d, status: 'example' as const } : d)),
    regionalLive: { smap: false, grace: false, soilSource: null }, nasaNow: null,
    extras: { openet: null, stress: null, insurance: null, water: null }, prov,
  };
}
const r4 = (v: number) => Math.round(v * 1e4) / 1e4;
/** The API's id for a point: pt_<n|s><lat x 1e4>_<e|w><lon x 1e4>. */
export const spotId = (lat: number, lon: number) => `pt_${lat >= 0 ? 'n' : 's'}${Math.round(Math.abs(lat) * 1e4)}_${lon >= 0 ? 'e' : 'w'}${Math.round(Math.abs(lon) * 1e4)}`;
/** The point back from a spot id (for a shared #spot= link). */
export function spotPoint(id: string): { lat: number; lon: number } | null {
  const m = /^pt_([ns])(\d+)_([ew])(\d+)$/.exec(id);
  if (!m) return null;
  const lat = (m[1] === 's' ? -1 : 1) * +m[2] / 1e4, lon = (m[3] === 'w' ? -1 : 1) * +m[4] / 1e4;
  return Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { lat, lon } : null;
}
/** A 200 m square around a point, as a field outline. */
function square200(lat: number, lon: number) {
  const dLat = 100 / 111320, dLon = 100 / (111320 * Math.cos((lat * Math.PI) / 180));
  return { type: 'Polygon' as const, coordinates: [[[lon - dLon, lat - dLat], [lon + dLon, lat - dLat], [lon + dLon, lat + dLat], [lon - dLon, lat + dLat], [lon - dLon, lat - dLat]]] };
}
/** The panel's stand-in while the spot is analysed: the point, a 200 m square, no data (the panel shows skeletons). */
export function spotPlaceholder(lat: number, lon: number): Location {
  const id = spotId(lat, lon);
  const base = baseFor({ id });
  return { ...base, id, name: 'Tapped spot', short_name: 'Tapped spot', farmer_name: 'Tapped spot', county: undefined, county_name: null, family: 'other', region: 'ca', dwr_id: undefined,
    geometry: square200(lat, lon), centroid: { lat, lon }, area_ha: { value: 4, low: null, high: null, unit: 'ha', method: 'assumed' }, crop_history: {}, events: [],
    water: { ...base.water, allocation_input: { unit: 'acre-ft/acre', value: 3.0 } }, spot: { state: 'loading', lat, lon } };
}
export type SpotResult = { kind: 'ok'; loc: Location; prov: ProvMap } | { kind: 'preset'; id: string } | { kind: 'error'; message: string; retryAfter?: number };
/** GET /api/analyze?lat=&lon= (4 decimals). Cold 2-5 s (up to about 8, more on a sleeping server), cached instantly. */
export async function analyzeSpot(lat: number, lon: number): Promise<SpotResult> {
  const ctl = new AbortController();
  const h = setTimeout(() => ctl.abort(), 55000);
  try {
    const r = await fetch(`${API_BASE}/analyze?lat=${r4(lat).toFixed(4)}&lon=${r4(lon).toFixed(4)}`, { signal: ctl.signal });
    if (r.status === 429) { const s = +(r.headers.get('Retry-After') ?? '') || undefined; return { kind: 'error', message: 'Busy, try again in a moment.', retryAfter: s }; }
    if (r.status === 422) return { kind: 'error', message: 'That spot cannot be analysed (the coordinates are out of range).' };
    if (r.status === 504) return { kind: 'error', message: 'No answer after 45 seconds. Try again.' };
    if (!r.ok) return { kind: 'error', message: 'The analysis did not work this time. Try again.' };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const b: any = await r.json();
    if (b?.analysis?.matches_preset) return { kind: 'preset', id: b.analysis.matches_preset };
    if (!b?.geometry || !b?.id) return { kind: 'error', message: 'The analysis came back empty. Try again.' };
    const { loc, prov } = realLocation(baseFor(b), b);
    const sec = (b.sections ?? {}) as Record<string, { status: string; reason?: string; fallback?: string; cropland?: boolean }>;
    const fallbackSquare = sec.boundary?.fallback === 'square_200m';
    prov.outline = P('outline', 'Spot outline', 'api', fallbackSquare ? '200 m square around your tap, not a field outline' : 'DWR / Land IQ 2023 field outline at your tap');
    const spot: Location['spot'] = { state: 'ready', lat: b.analysis?.point?.lat ?? lat, lon: b.analysis?.point?.lon ?? lon, sections: b.sections, fallbackSquare, cropland: sec.family?.cropland !== false };
    return { kind: 'ok', loc: { ...loc, events: [], spot, county_name: b.county_name ?? null, county: b.county_name ?? undefined }, prov };
  } catch {
    return { kind: 'error', message: ctl.signal.aborted ? 'No answer after 45 seconds. Try again.' : 'Could not reach the CropLytics server, or it is busy. Try again in a moment.' };
  } finally { clearTimeout(h); }
}
// ---------- satellite calendar (backend/field/out/<id>/calendar.json) -> 10-day steps ----------
const CLS: Record<string, CoverClass> = { bare: 'b', partial: 'p', covered: 'c', water: 'w', unknown: 'u' };
const doy = (y: number, m: number, d: number) => Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 0)) / 864e5);
const dekadDate = (y: number, k: number) => [y, Math.floor(k / 3) + 1, [5, 15, 25][k % 3]] as const;
interface RealCalYear { year: number; segments: { start_doy: number; end_doy: number; class: string }[]; markers: { date: string; type: string }[]; observations: { date: string; ndvi: number | null; class: string }[] }
/** A year with no processed imagery yet (2026): every 10-day step is "no reading". Drawn hatched, never guessed. */
const blankYear = (year: number, cdl = 'Not published yet'): CalendarYear => ({ year, cdl, rule: 'u'.repeat(36), ml: 'u'.repeat(36), ndvi: Array(36).fill(0), et_mm_day: Array(36).fill(0), greenup_dekad: null, senescence_dekad: null, risks: [] });
/** Pad a calendar to YEARS (the bundled mock stops at 2025). */
const padCalendar = (c: Calendar | undefined): Calendar => ({ ...(c as Calendar), years: YEARS.map((y, i) => (c?.years ?? []).find((x) => x.year === y) ?? (c?.years ?? [])[i] ?? blankYear(y)) });
/** One year of a real calendar (rule or ML) as 36 ten-day classes. */
function classString(ry: RealCalYear | undefined, year: number) {
  if (!ry) return 'u'.repeat(36);
  let out = '';
  for (let k = 0; k < 36; k++) { const [y, m, d] = dekadDate(year, k), q = doy(y, m, d); const seg = ry.segments.find((s) => q >= s.start_doy && q <= s.end_doy); out += CLS[seg?.class ?? 'unknown'] ?? 'u'; }
  return out;
}
function convertCalendar(real: { years: RealCalYear[] }, mock: Calendar, hist: Record<string, string>, ml: { years: RealCalYear[] } | null): Calendar {
  const years: CalendarYear[] = YEARS.map((year, yi) => {
    const ry = (real?.years ?? []).find((y) => y.year === year);
    const my = mock?.years?.[yi] ?? blankYear(year, hist[year] ?? 'Not published yet');
    if (!ry) return year > 2025 ? blankYear(year, hist[year] ?? 'Not published yet') : my;
    const obs = ry.observations.filter((o) => o.ndvi != null).map((o) => ({ t: Date.parse(o.date), v: o.ndvi as number }));
    const rule = classString(ry, year);
    const ndvi: number[] = [];
    for (let k = 0; k < 36; k++) {
      const [y, m, d] = dekadDate(year, k), tt = Date.UTC(y, m - 1, d);
      const i = obs.findIndex((o) => o.t >= tt);
      const a = obs[i - 1], b = obs[i];
      ndvi.push(a && b && b.t - a.t <= 30 * 864e5 ? a.v + ((b.v - a.v) * (tt - a.t)) / (b.t - a.t || 1) : (b ?? a)?.v ?? 0);
    }
    const dk = (iso?: string) => { if (!iso) return null; const [, m, d] = iso.split('-').map(Number); return (m - 1) * 3 + (d <= 10 ? 0 : d <= 20 ? 1 : 2); };
    const up = ry.markers.find((m) => m.type === 'green_up' && m.date.startsWith(String(year)));
    const dn = ry.markers.find((m) => m.type === 'senescence_harvest' && m.date.startsWith(String(year)) && (!up || m.date > up.date));
    // ML calendar (GET .../calendar_ml) when it exists; otherwise "no reading" so the comparison never shows a copy of the rule
    const mlStr = ml ? classString((ml?.years ?? []).find((y) => y.year === year), year) : 'u'.repeat(36);
    // crop water use per 10-day step and the risk ticks stay from the bundled example (no route yet)
    return { ...my, year, cdl: hist[year] ?? my.cdl, rule, ml: mlStr, ndvi, greenup_dekad: dk(up?.date), senescence_dekad: dk(dn?.date) };
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
const CROP_LABEL: Record<string, string> = { alfalfa_hay_bc: 'alfalfa', barley_silage_bc: 'barley silage', fall_cereal_silage_bc: 'fall rye silage', sainfoin_grass_bc: 'sainfoin-grass', open_water_flood: 'flood', rice_medium_grain: 'rice', cereal_vetch_cover: 'cereal + vetch cover', safflower: 'safflower', winter_wheat: 'winter wheat', alfalfa_hay: 'alfalfa', small_grain_silage: 'small-grain silage', silage_corn: 'silage corn', sorghum_sudan: 'sorghum-sudan' };
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
  const rep = (y: string) => {
    const raw = s.exposure.replay?.[y];
    const irrNote = raw?.irrigation_need_mm?.note;
    const note = typeof raw?.note === 'string' && raw.note
      ? raw.note
      : typeof irrNote === 'string' && /replay/i.test(irrNote)
        ? (y === '2022' ? 'Dry year replay: less rain, more heat and pumping.' : 'Wet year replay: more winter rain, less summer irrigation.')
        : raw?.irrigation_need_mm
          ? `Replay of ${y} weather at this field (NASA POWER).`
          : 'No replay for this year';
    return {
      irrigation_need_mm: raw?.irrigation_need_mm ?? s.water.irrigation_need_mm,
      exposed_rain_days: raw?.exposed_rain_days ?? s.exposure.exposed_rain_days,
      note,
    };
  };
  const rp = s.risk_profile;
  const r = (k: string) => (rp[k]?.value == null ? blank('share', rp[k]?.note ?? 'blocked', rp[k]?.source) : rp[k]);
  return {
    ...s,
    short_name: SHORT[s.id] ?? s.short_name ?? s.name.split(/[,(]/)[0].trim(),
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
export interface Scenario { dT_c: number; dP_pct: number }
/** The grower's answers on step 4: what the crop is for (market score) and the equipment they have (filters rotations out). */
export interface FarmAnswers { market_preference?: 'sell' | 'feed_own_herd' | 'no_preference'; constraints?: { has_seed_drill?: boolean } }
export async function scoreStrategies(id: string, allocation: number, weights?: Partial<Record<ScoreKey, number>>, scenario?: Scenario, farm?: FarmAnswers) {
  const b = await apiReal(`/api/locations/${id}/score`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ allocation, ...(weights ? { weights } : {}), ...(scenario ? { scenario } : {}), ...(farm ?? {}) }) });
  return b?.items ? (b.items as unknown[]).map(normStrategy) : null;
}

// ---------- news ----------
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const normNews = (n: any): NewsItem => ({ ...n, verified: !!n.url && !n.url.includes('news.google.com'), signal: { label: n.signal?.dataset ?? '', value_pct: null, lead_days: null, ...n.signal } });

/** 2023-2026 season strips for the pick list: 36 ten-day classes per year from the field calendar (HLS when served). */
export async function getStrips(ids: string[]): Promise<Record<string, Record<number, string>>> {
  if (!(await apiLive())) return {};
  const out: Record<string, Record<number, string>> = {};
  await Promise.all(ids.map(async (id) => {
    const c = (await apiReal(`/api/locations/${id}/calendar?source=hls`)) ?? (await apiReal(`/api/locations/${id}/calendar`));
    if (c?.years) out[id] = Object.fromEntries([2023, 2024, 2025, 2026].map((y) => [y, classString((c.years as RealCalYear[]).find((x) => x.year === y), y)]));
  }));
  return out;
}

// ---------- machine-learning calendar: how good is it? (GET .../models) ----------
/** estimate: the API's stand-in for a region the model was not trained for (BC): a simple rule checked against Sentinel-2's own scene labels (agreeScl). */
export interface MLInfo { acc2022: number | null; f1Bare2022: number | null; meetsTarget: boolean; inflated: boolean; disagreePct: number | null; model: string; estimate?: boolean; agreeScl?: number | null }
/** Accuracy target for the bare/cover detector, tested on 2022 (held out): accuracy >= 85% and bare-ground F1 >= 0.80 (backend/ai). */
export const ML_TARGET = { acc: 0.85, f1: 0.8 };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mlInfo(models: any, mlCal: any): MLInfo | null {
  if (!mlCal?.years) return null;
  if (mlCal._source === 'estimate') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const it = (models?.items ?? []).filter((x: any) => x.task === 'bare_cover' && x.metrics?.agreement_scl != null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const m = it.find((x: any) => /twoclass/.test(x.id)) ?? it[0];
    return { acc2022: null, f1Bare2022: null, meetsTarget: false, inflated: false, disagreePct: mlCal.disagreement_with_rule_obs_pct ?? null, model: 'two-class greenness rule (estimate)', estimate: true, agreeScl: m?.metrics?.agreement_scl ?? null };
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const m = (models?.items ?? []).find((x: any) => x.task === 'bare_cover' && x.method === (mlCal.detector ?? 'random_forest') && x.split?.type === 'year');
  const acc = m?.metrics?.accuracy_2022 ?? null, f1 = m?.metrics?.f1_bare_2022 ?? null;
  return { acc2022: acc, f1Bare2022: f1, meetsTarget: acc != null && f1 != null && acc >= ML_TARGET.acc && f1 >= ML_TARGET.f1, inflated: acc != null && acc > 0.97,
    disagreePct: mlCal.disagreement_with_rule_obs_pct ?? null, model: String(mlCal.detector ?? 'random_forest').replace(/_/g, ' ') };
}

// ---------- regional NASA series (GET .../nasa_series: one row per 10-day step from 2015) ----------
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function seriesOf(b: any, key: string): (number | null)[] | null {
  if (!b?.rows) return null;
  const out: (number | null)[] = Array(YEARS.length * 36).fill(null);
  let n = 0;
  for (const r of b.rows as Record<string, unknown>[]) {
    const v = r[key];
    if (typeof r.date !== 'string' || typeof v !== 'number') continue;
    const t = dateToT(r.date);
    if (t >= 0 && t < out.length) { out[t] = v; n++; }
  }
  return n ? out : null;
}

// ---------- crop stress (backend/ai), water seen (NASA OPERA), measured water use (OpenET), crop insurance (USDA RMA) ----------
export interface StressWeek { start: string; status: 'one' | 'both'; drivers: string[]; tmaxC: number | null; crop: string }
export interface WaterScene { date: string; frac: number }
export interface Extras {
  openet: { month: string; in: number }[] | null;
  stress: { weeks: StressWeek[]; evaluated: Record<number, number> } | null;
  insurance: Location['rma'] | null;
  water: { scenes: WaterScene[]; summary: string | null; seasons: { season: string; seen: boolean; clear: number }[] } | null;
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extrasOf(oet: any, st: any, ins: any, w: any, ns: any, prov: ProvMap, used: Partial<Record<string, NasaStatus>>): Extras {
  const openet = oet?.rows?.length ? (oet.rows as { month?: string; date: string; et_in?: number; et_mm?: number }[]).map((r) => ({ month: r.month ?? r.date.slice(0, 7), in: r.et_in ?? (r.et_mm ?? 0) / 25.4 })) : null;
  if (openet) prov.openet = P('openet', 'Measured crop water use (OpenET)', orig(oet), `${openet.length} months`);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const wk: any[] = st?.weeks ?? st?.items ?? [];
  const evaluated: Record<number, number> = {};
  for (const x of wk) if (x.evaluated) evaluated[x.iso_year] = (evaluated[x.iso_year] ?? 0) + 1;
  const stress = wk.length ? { weeks: wk.filter((x) => x.status === 'one' || x.status === 'both').map((x) => ({ start: x.week_start, status: x.status, drivers: x.drivers ?? [], tmaxC: x.tmax_c ?? null, crop: x.crop ?? '' })), evaluated } : null;
  if (stress) prov.stress = P('stress', 'Crop-stress weeks (two statistical methods)', orig(st), `${stress.weeks.length} weeks flagged`);
  // insurance: route shape may be the rma_profile file (profiles) or a flat summary
  const pr = ins?.profiles ? (Object.values(ins.profiles)[0] as any) : ins; // eslint-disable-line @typescript-eslint/no-explicit-any
  let insurance: Location['rma'] | null = null;
  if (pr?.total_indemnity_usd != null) {
    const by = (pr.indemnity_by_year_usd ?? {}) as Record<string, number>, ys = Object.keys(by).map(Number);
    const top = ys.sort((x, y) => by[y] - by[x])[0];
    insurance = { scope: pr.scope ?? '', crop: pr.crop ?? '', total_usd: pr.total_indemnity_usd, from: Math.min(...ys), to: Math.max(...ys), top_year: top, top_usd: by[top] ?? 0,
      share_drought: pr.shares?.share_drought?.value ?? pr.share_drought ?? 0, share_excess_moisture: pr.shares?.share_excess_moisture?.value ?? null, source: 'USDA RMA Cause of Loss', url: ins.page_url ?? '' };
    prov.rma = P('rma', 'Crop-insurance payouts (USDA RMA)', orig(ins), `${insurance.from}–${insurance.to}`);
  }
  else if (pr && orig(ins) === 'estimate') {
    // BC: no loss records, so no dollars on purpose; only the estimated share of losses by cause
    const src = (pr.shares ?? pr) as Record<string, unknown>;
    const v = (x: unknown) => (typeof x === 'number' ? x : typeof (x as { value?: unknown })?.value === 'number' ? (x as { value: number }).value : null);
    const shares = Object.entries(src).filter(([k]) => /^share_/.test(k)).map(([k, x]) => ({ cause: k.replace(/^share_/, ''), share: v(x) })).filter((x): x is { cause: string; share: number } => x.share != null && x.share > 0);
    if (shares.length) {
      insurance = { scope: pr.scope ?? '', crop: pr.crop ?? '', total_usd: null, from: 0, to: 0, top_year: 0, top_usd: 0, share_drought: shares.find((x) => x.cause === 'drought')?.share ?? 0,
        share_excess_moisture: shares.find((x) => x.cause === 'excess_moisture')?.share ?? null, source: 'Estimate', url: '', shares: shares.sort((a, b) => b.share - a.share) };
      prov.rma = P('rma', 'Crop-loss causes (estimate)', 'estimate', 'shares by cause, no dollars');
    }
  }
  // water seen: GET .../water_seen (OPERA scenes), else the OPERA column of nasa_series
  let water: Extras['water'] = null;
  if (w?.scenes?.length) {
    water = { scenes: (w.scenes as { date: string; water_frac: number; clear: boolean }[]).filter((x) => x.clear).map((x) => ({ date: x.date, frac: x.water_frac })), summary: w.summary ?? null,
      seasons: (w.seasons ?? []).map((x: { season: string; water_seen: boolean; clear_scenes: number }) => ({ season: x.season, seen: x.water_seen, clear: x.clear_scenes })) };
  } else if (ns?.rows) {
    const sc = (ns.rows as Record<string, unknown>[]).filter((r) => typeof r.dswx_water_frac === 'number').map((r) => ({ date: String(r.date), frac: r.dswx_water_frac as number }));
    if (sc.length) water = { scenes: sc, summary: null, seasons: [] };
  }
  if (water) { prov.water_seen = P('water_seen', 'Standing water seen (NASA OPERA)', w?.scenes?.length ? orig(w) : 'api', `${water.scenes.length} clear views`); used.opera = 'live'; }
  return { openet, stress, insurance, water };
}

// ---------- everything the field view needs ----------
export interface FieldBundle { id: string; cells: CellGrid | null; cal: Calendar; regional: Regional | null; strategies: RotationStrategy[]; news: NewsItem[]; ml: MLInfo | null; nasa: NasaDataset[]; regionalLive: RegionalLive; nasaNow: NasaNow | null; extras: Extras; prov: ProvMap }
/** GET .../nasa_now: today's NASA readings. Rain since 1 Oct from GPM IMERG and its 2001-2025 normal (mm). */
export interface NasaNow { rainWyMm: number | null; rainWyNormalMm: number | null; rainDate: string | null; dswxWater: number | null; dswxDate: string | null }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const nowOf = (b: any): NasaNow | null => { const r = b?.readings; if (!r) return null; return { rainWyMm: r.imerg_wy_to_date_mm?.value ?? null, rainWyNormalMm: r.imerg_wy_to_date_normal_mm?.value ?? null, rainDate: r.imerg_wy_to_date_mm?.obs_date ?? null, dswxWater: r.dswx_water_frac?.value ?? null, dswxDate: r.dswx_water_frac?.obs_date ?? null }; };
/** Which soil-moisture / groundwater readings are real. soilSource says whose soil reading it is. */
export interface RegionalLive { smap: boolean; grace: boolean; soilSource?: 'smap' | 'grace_da' | null }
/** Everything the field view needs. Resolves as soon as the answers' data is in; the 3D grid and the news arrive later through onLate. */
export async function getField(loc: Location, live: boolean, onLate?: (b: FieldBundle) => void, caPresets?: Location[]): Promise<FieldBundle> {
  const id = loc.id, lite = isLite(id), presets = caPresets ?? MOCK_LOCS, borrow = lite ? nearestCaPreset(loc, presets) : id;
  const mid = templateId(id, loc.family); // mid: the bundled example used until the API answers
  const dataId = lite ? borrow : id;
  const mCal = padCalendar((mockCalendar as unknown as ById<Calendar>)[lite ? borrow : mid] ?? (mockCalendar as unknown as ById<Calendar>)[mid]);
  const prov: ProvMap = {
    calendar: P('calendar', 'Bare / green / flooded calendar', 'mock', 'illustrative'),
    grid: P('grid', '100 ft squares in the 3D view', 'mock', 'illustrative'),
    strategies: P('strategies', 'Rotations, water need and scores', 'mock', 'illustrative'),
    news: P('news', 'News headlines', 'mock', 'project brief examples'),
    regional: P('regional', 'Soil moisture (SMAP) and groundwater (GRACE-FO)', 'mock', 'no real series served yet'),
    ml: P('ml', 'Machine-learning calendar', 'mock', 'not served'),
  };
  const reg0 = (regional as unknown as ById<Regional>)[lite ? borrow : mid];
  const used: Partial<Record<string, NasaStatus>> = loc.nasadem ? { nasadem: 'live' } : {};
  const nasa = () => nasaList(loc.nasa_datasets, loc.datasets, { ...used, ...(soilExample() ? { smap: 'example' as const } : {}) }).list;
  let soilShown: 'smap' | 'grace_da' | null = null;
  const soilExample = () => soilShown == null; // the soil answer shows SMAP example numbers when no real soil series came back
  const borrowNote = lite ? `nearest prepared field (${borrow})` : '';
  if (!live) {
    const cells = gridAt(loc, lite ? borrow : mid) ?? gridAt(loc, 'car_colusa_rice');
    return {
      id, regional: reg0, cells, cal: calFor(mCal, id), strategies: lite ? [] : mockStrats(mid), news: lite ? [] : (mockNews as unknown as ById<NewsItem[]>)[mid],
      ml: null, nasa: nasa().map((d) => (d.status === 'live' && d.id !== 'iss' ? { ...d, status: 'example' as const } : d)),
      regionalLive: { smap: false, grace: false, soilSource: null }, nasaNow: null, extras: { openet: null, stress: null, insurance: null, water: null }, prov,
    };
  }
  const fetchGrid = async () => {
    const own = await gridFetch(id);
    if (own?.features) return { grid: own, shifted: false };
    if (!lite) return { grid: null, shifted: false };
    const near = await gridFetch(borrow);
    return { grid: near, shifted: !!near?.features };
  };
  const lateP = Promise.all([fetchGrid(), lite ? Promise.resolve(null) : apiReal(`/api/locations/${id}/news`)]);
  prefetchFieldStack(loc, presets);
  const stratP = apiReal(`/api/locations/${id}/strategies`, undefined, lite ? 45000 : 12000);
  const stackP = Promise.all([
    apiReal(`/api/locations/${dataId}/calendar`),
    apiReal(`/api/locations/${dataId}/calendar?source=hls`),
    lite ? apiReal(`/api/locations/${borrow}/calendar_ml`) : apiReal(`/api/locations/${id}/calendar_ml`),
    lite ? apiReal(`/api/locations/${borrow}/models`) : apiReal(`/api/locations/${id}/models`),
    apiReal(`/api/locations/${dataId}/nasa_series`),
  ]);
  const presetP = lite ? null : Promise.all([
    apiReal(`/api/locations/${id}/nasa_now`),
    apiReal(`/api/locations/${id}/openet`),
    apiReal(`/api/locations/${id}/stress`),
    apiReal(`/api/locations/${id}/insurance`),
    apiReal(`/api/locations/${id}/water_seen`),
  ]);
  const [cal, hls, mlCal, models, ns] = await stackP;
  const strat = await (lite ? Promise.race([
    stratP,
    new Promise<null>((r) => setTimeout(() => r(null), lite ? 1800 : 12000)),
  ]) : stratP);
  let now: Awaited<ReturnType<typeof apiReal>> = null, oet = null, stressB = null, insB = null, waterB = null;
  if (presetP) [now, oet, stressB, insB, waterB] = await presetP;
  // Stand-in squares on this outline until /grid returns (unshifted template grids drew the stack on the wrong field).
  let c = calFor(mCal, id), cells: CellGrid | null = gridAt(loc, lite ? borrow : mid) ?? gridAt(loc, 'car_colusa_rice'), strategies = mockStrats(mid), nws = id === mid ? (mockNews as unknown as ById<NewsItem[]>)[mid] : [];
  // NASA first: the HLS calendar wins when the API serves it (it says so in its sources)
  const isHls = !!hls?.years && /hls/i.test(JSON.stringify(hls.source ?? hls.sources ?? hls.calendar_source ?? hls.method ?? ''));
  const calSrc = isHls ? hls : cal;
  const ml = mlInfo(models, mlCal);
  if (calSrc?.years) {
    c = calFor(convertCalendar(calSrc, mCal, loc.crop_history, mlCal?.years ? mlCal : null), id);
    prov.calendar = P('calendar', 'Bare / green / flooded calendar', 'api', `${isHls ? 'NASA/USGS HLS, greenness rule' : 'Landsat (NASA/USGS) and Sentinel-2, greenness rule'}${borrowNote ? ` · ${borrowNote}` : ''}`);
    used.landsat = 'live';
    if (isHls) used.hls = 'live';
  }
  if (mlCal?.years) prov.ml = P('ml', 'Machine-learning calendar (comparison)', orig(mlCal), `${ml?.model ?? 'random forest'}, Sentinel-2`);
  if (strat?.items?.length) { strategies = strat.items.map(normStrategy); prov.strategies = P('strategies', 'Rotations, water need and scores', orig(strat), lite ? 'rotation model, NASA POWER weather for this field' : 'rotation model, NASA POWER weather'); used.power = 'live'; }
  else if (lite) prov.strategies = P('strategies', 'Rotations, water need and scores', 'mock', 'still loading or unavailable');
  let reg = reg0;
  // GET .../nasa_series: SMAP root-zone percentile when cached; otherwise NASA's GRACE-FO data-assimilation root-zone percentile
  const smapS = seriesOf(ns, 'smap_rootzone_pct'), gdaSoil = seriesOf(ns, 'grace_rootzone_pct');
  const sm = smapS ?? gdaSoil, gr = seriesOf(ns, 'grace_gw_pct');
  const soilSource: 'smap' | 'grace_da' | null = smapS ? 'smap' : gdaSoil ? 'grace_da' : null;
  soilShown = soilSource;
  if (reg0 && (sm || gr)) {
    reg = { ...reg0, smap_rootzone_pct: sm ? { ...reg0.smap_rootzone_pct, values: sm } : reg0.smap_rootzone_pct, grace_gw_pct: gr ? { ...reg0.grace_gw_pct, values: gr } : reg0.grace_gw_pct };
    if (smapS) used.smap = 'live';
    if (gr || gdaSoil) used.grace = 'live';
    if (/imerg/.test(JSON.stringify(ns?.sources ?? ''))) used.imerg = 'live'; // rain so far this season reads IMERG from the daily record
    prov.regional = P('regional', 'Soil moisture and groundwater (NASA SMAP / GRACE-FO)', sm && gr ? 'api' : 'mock', `${soilSource === 'smap' ? 'SMAP' : soilSource === 'grace_da' ? 'GRACE-FO data assimilation (SMAP not cached yet)' : 'soil: example numbers'}; ${gr ? 'GRACE-FO groundwater' : 'groundwater: example numbers'}${borrowNote ? ` · ${borrowNote}` : ''}`);
  } else if (lite && reg0) {
    reg = reg0;
    prov.regional = P('regional', 'Soil moisture and groundwater (NASA SMAP / GRACE-FO)', 'mock', `example numbers · ${borrowNote}`);
  }
  const extras = lite ? { openet: null, stress: null, insurance: null, water: null } : extrasOf(oet, stressB, insB, waterB, ns, prov, used);
  const first: FieldBundle = { id, regional: reg, cells, cal: c, strategies, news: nws, ml, nasa: nasa(), regionalLive: { smap: !!sm, grace: !!gr, soilSource }, nasaNow: nowOf(now), extras, prov };
  if (lite) {
    stratP.then((st) => {
      if (!st?.items?.length) return;
      const strategies2 = st.items.map(normStrategy);
      const p2 = { ...prov, strategies: P('strategies', 'Rotations, water need and scores', orig(st), 'rotation model, NASA POWER weather for this field') };
      used.power = 'live';
      setTimeout(() => onLate?.({ ...first, strategies: strategies2, prov: p2 }), 0);
    });
  }
  lateP.then(([gridRes, news]) => {
    const p2 = { ...prov };
    let cells2: CellGrid | null = cells, nws2 = nws;
    const grid = gridRes?.grid;
    if (grid?.features) {
      let g = convertGrid(grid);
      if (gridRes.shifted) {
        const bc = presetCentroid(borrow, presets) ?? loc.centroid;
        g = shiftGrid(g, loc.centroid.lon - bc.lon, loc.centroid.lat - bc.lat);
      }
      cells2 = g;
      p2.grid = P('grid', '100 ft squares in the 3D view', 'api', `${cells2.features.length} squares, Sentinel-2 greenness${gridRes.shifted ? ` · shifted from ${borrow}` : ''}`);
    }
    if (news?.items?.length) { nws2 = news.items.map(normNews); p2.news = P('news', 'News headlines', 'api', `${news.items.length} saved headlines`); }
    // after the caller has stored `first` (a late result must not be overwritten by the early one)
    if (cells2 !== cells || nws2 !== nws) setTimeout(() => onLate?.({ ...first, cells: cells2, news: nws2, prov: p2 }), 0);
  });
  return first;
}

// ---------- ISS astronaut photos (copied into public/iss/<id>/ from data/cache/<id>/iss) ----------
export interface ISSPhoto { photo_id: string; date: string; center_lat: number; center_lon: number; lens_mm: number; features: string; page_url: string; file: string; url: string; miles: number }
export async function getISS(loc: Location): Promise<{ photo: ISSPhoto; credit: string } | null> {
  try {
    const j = await getJSON(`${BASE}iss/${loc.id}/iss.json`);
    const mi = (p: ISSPhoto) => Math.hypot((p.center_lat - loc.centroid.lat) * 69, (p.center_lon - loc.centroid.lon) * 69 * Math.cos((loc.centroid.lat * Math.PI) / 180));
    const ps = (j.photos as ISSPhoto[]).map((p) => ({ ...p, url: `${BASE}iss/${loc.id}/${p.file}`, miles: mi(p) })).sort((a, b) => a.miles - b.miles);
    return ps[0] ? { photo: ps[0], credit: j.credit } : null;
  } catch { return null; }
}

// ---------- daily weather (GET .../daily): NOAA station means + NASA POWER reference ET ----------
export async function getDaily(id: string): Promise<{ daily: Daily | null; prov: Prov }> {
  let b = await apiReal(`/api/locations/${id}/daily`, undefined, isLite(id) ? 30000 : 12000);
  // a spot's record is built on its first read and may miss once while the analysis settles: one retry
  if (!b?.rows?.length && isLite(id)) { await new Promise((r) => setTimeout(r, 1500)); b = await apiReal(`/api/locations/${id}/daily`, undefined, 30000); }
  if (!b?.rows?.length) return { daily: null, prov: P('daily', 'Rain (NASA GPM IMERG), heat and frost (NOAA stations)', 'mock', 'daily route not reachable') };
  const rows = b.rows as Daily['rows'];
  const net = b.station_network === 'ECCC' ? 'Environment Canada stations' : 'NOAA stations';
  if (isLite(id)) return { daily: { rows, first: rows[0].date, last: rows[rows.length - 1].date }, prov: P('daily', 'Rain, heat and crop water demand (NASA POWER, this spot)', 'api', `daily record ${rows[0].date.slice(0, 4)}–${rows[rows.length - 1].date.slice(0, 7)}`) };
  return { daily: { rows, first: rows[0].date, last: rows[rows.length - 1].date }, prov: P('daily', `Rain (NASA GPM IMERG), heat and frost (${net})`, 'api', `daily record ${rows[0].date.slice(0, 4)}–${rows[rows.length - 1].date.slice(0, 7)}`) };
}

// ---------- coming-season outlooks ----------
// GET .../outlook (backend/outlook) -> else src/mock/outlook.example.json, labelled as example numbers.
export interface OutlookCat { category: string; prob: number | null }
export interface OutlookSeason { season: string; temp: OutlookCat | null; rain: OutlookCat | null }
export interface Reservoir { id: string; name: string; storageAf: number; capacityAf: number | null; pctAvg: number | null; pctCap: number | null; yearAgoAf: number | null; date: string }
export interface Outlook {
  issued: string | null; seasons: OutlookSeason[];
  droughtNow: { category: string; date: string; county: string } | null;
  droughtOutlook: { category: string; target: string; issued: string } | null;
  reservoirs: Reservoir[];
  allocations: { project: string; items: { year: number; pct: number }[]; next: string; url: string } | null;
  /** From backend/outlook outlook.json when present */
  cvpNow?: { settlement: number | null; northAg: number | null; southAg: number | null; updated: string } | null;
  swpNow?: { pct: number; verified: boolean } | null;
  storageVsAlloc?: { year: number; shastaPctCap: number; southAg: number | null; settlement: number | null; partial: boolean }[];
  shastaNowAf?: number | null;
  nextAnnouncements?: string[];
  snow?: { swe: number | null; date: string; b120: string } | null;
  bare?: { start: string; end: string; days: number | null; low: number | null; high: number | null; chance: number | null; chanceLo: number | null; chanceHi: number | null; chanceOutlook: number | null; note: string } | null;
  irrigation?: Record<string, { value: number; low: number; high: number }>;
  prov: { cpc: Prov; water: Prov; alloc: Prov };
  /** true when the API has no outlook built for this field yet (404) */
  notReady?: boolean;
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const num = (x: any): number | null => (x == null ? null : typeof x === 'number' ? x : typeof x.value === 'number' ? x.value : null);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cat = (x: any): OutlookCat | null => (x?.category ? { category: String(x.category), prob: num(x.probability) } : null);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function adaptOutlook(o: any, w: any, al: any, origin: { cpc: Origin; water: Origin; alloc: Origin }, detail: string): Outlook {
  const seasons: OutlookSeason[] = (o?.seasons ?? []).map((s: any) => ({ season: s.season, temp: cat(s.temperature), rain: cat(s.precipitation) })); // eslint-disable-line @typescript-eslint/no-explicit-any
  const issued = o?.seasons?.[0]?.temperature?.issued ?? o?.seasons?.[0]?.issued ?? null;
  const so = o?.drought_outlook?.seasonal;
  const dm = w?.drought_monitor;
  const res = Object.entries(w?.reservoirs ?? {}).map(([id, r]: [string, any]) => ({ // eslint-disable-line @typescript-eslint/no-explicit-any
    id, name: String(r.name ?? id), storageAf: num(r.storage_af) ?? 0, capacityAf: num(r.capacity_af), pctAvg: num(r.pct_of_cdec_average) ?? num(r.pct_of_own_average), pctCap: num(r.pct_of_capacity), yearAgoAf: num(r.storage_year_ago_af), date: String(r.latest_daily_date ?? r.cdec_report_date ?? ''),
  }));
  return {
    issued, seasons,
    droughtNow: dm ? { category: String(dm.worst_category), date: String(dm.map_date), county: String(dm.county ?? '') } : null,
    droughtOutlook: so ? { category: String(so.category), target: String(so.target ?? ''), issued: String(so.issued ?? '') } : null,
    reservoirs: res,
    allocations: al ?? null,
    prov: {
      cpc: P('outlook_cpc', 'Winter rain, temperature and drought outlooks (NOAA)', origin.cpc, detail),
      water: P('outlook_water', 'Drought Monitor and reservoir storage now (CDEC)', origin.water, detail),
      alloc: P('outlook_alloc', 'Water allocation history', origin.alloc, origin.alloc === 'mock' ? 'example file; no backend source yet' : detail),
    },
  };
}
const outlookGap = (detail: string): Outlook => ({
  issued: null, seasons: [], droughtNow: null, droughtOutlook: null, reservoirs: [], allocations: null, notReady: true,
  prov: {
    cpc: P('outlook_cpc', 'Winter outlooks (NOAA)', 'api', detail),
    water: P('outlook_water', 'Drought and reservoirs', 'api', detail),
    alloc: P('outlook_alloc', 'Water allocations', 'api', detail),
  },
});
export async function getOutlook(id: string, live: boolean): Promise<Outlook> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ex = outlookExample as any;
  const exAlloc = ex.presets[id]?.allocations ?? null;
  // presets + freeform (pt_/my_): API returns a real file; freeform uses the nearest CA prepared field
  const { body: full, missing } = live ? await apiRealOr404(`/api/locations/${id}/outlook`) : { body: null, missing: false };
  if (full) {
    const o = fromOutlookFile(full.presets?.[id] ?? full, exAlloc, orig(full));
    if (full.for_freeform && full.note) o.prov.cpc = { ...o.prov.cpc, detail: String(full.note) };
    return o;
  }
  if (missing || (live && !ex.presets[id] && !isLite(id))) return outlookGap('not ready for this field yet');
  if (missing && isLite(id)) return outlookGap(isMine(id) ? 'winter outlook not available for this drawn field yet' : 'winter outlook not available for this tapped spot yet');
  return adaptOutlook(ex.example_full, ex.example_full, exAlloc, { cpc: 'mock', water: 'mock', alloc: 'mock' }, 'example file');
}

const MD = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const mdText = (mmdd?: string) => { if (!mmdd) return ''; const [m, d] = mmdd.split('-').map(Number); return `${d <= 10 ? 'early' : d <= 20 ? 'mid' : 'late'} ${MD[m - 1]}`; };
/** backend/outlook/out/<id>/outlook.json (the coming-season file built by backend/outlook) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fromOutlookFile(j: any, exAlloc: any, origin: Origin): Outlook {
  const base = adaptOutlook({ ...j.cpc_seasonal_outlook, drought_outlook: j.drought?.cpc_drought_outlook }, { drought_monitor: j.drought?.us_drought_monitor, reservoirs: j.reservoirs_now }, null,
    { cpc: origin, water: origin, alloc: origin }, `backend/outlook, ${String(j.generated_at ?? '').slice(0, 10)}`);
  base.issued = j.cpc_seasonal_outlook?.issued ?? base.issued;
  const a = j.allocations_context ?? {}, cvp = a.cvp?.wy2026, sva = a.storage_vs_final_allocation;
  base.cvpNow = cvp ? { settlement: num(cvp.sacramento_river_settlement_contractors), northAg: num(cvp.north_of_delta_ag), southAg: num(cvp.south_of_delta_ag), updated: String(a.cvp?.latest_update ?? '') } : null;
  base.swpNow = a.swp?.latest ? { pct: num(a.swp.latest) ?? 0, verified: !!a.swp.latest.verified } : null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  base.storageVsAlloc = (sva?.rows ?? []).map((r: any) => ({ year: r.allocation_year, shastaPctCap: r.pct_of_capacity, southAg: r.cvp_south_of_delta_ag_pct ?? null, settlement: r.cvp_settlement_contractors_pct ?? null, partial: !!r.partial_year }));
  base.shastaNowAf = sva?.shasta_13nov_2026_af ?? null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  base.nextAnnouncements = (j.blocked_or_not_yet_published ?? []).map((b: any) => `${b.item}: ${b.status}`);
  const sn = j.snowpack_runoff;
  base.snow = sn ? { swe: num(sn.snow_now_statewide?.swe_inches), date: String(sn.snow_now_statewide?.report_date ?? ''), b120: String(sn.bulletin_120?.status ?? '') } : null;
  const f = j.field_expectations_from_history ?? {}, bw = f.bare_window, hr = f.heavy_rain_in_window ?? {};
  base.bare = bw?.median_start ? {
    start: mdText(bw.median_start), end: mdText(bw.median_end), days: num(bw.median_days), low: bw.median_days?.low ?? null, high: bw.median_days?.high ?? null,
    chance: num(hr.chance_any_day_ge_25mm_climatology), chanceLo: hr.chance_any_day_ge_25mm_climatology?.low ?? null, chanceHi: hr.chance_any_day_ge_25mm_climatology?.high ?? null,
    chanceOutlook: num(hr.chance_given_cpc_outlook), note: '',
  } : { start: '', end: '', days: null, low: null, high: null, chance: null, chanceLo: null, chanceHi: null, chanceOutlook: null, note: String(bw?.note ?? f.note ?? 'No typical bare window') };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  base.irrigation = Object.fromEntries((j.irrigation_2027?.strategies ?? []).map((s: any) => [s.id, { value: num(s.irrigation_need_af_ac) ?? 0, low: s.irrigation_need_af_ac?.low ?? 0, high: s.irrigation_need_af_ac?.high ?? 0 }]));
  base.allocations = exAlloc ? { ...exAlloc, items: [] } : null; // only the grower-facing note (GSA for groundwater fields); history comes from storageVsAlloc
  base.prov.alloc = P('outlook_alloc', 'Water allocations (Reclamation CVP table; SWP via ACWA)', origin, 'backend/outlook');
  return base;
}

// ---------- Ask CropLytics chat (backend app/chat) ----------
export interface ChatTurn { role: 'user' | 'assistant'; content: string }
let chatOn: Promise<{ enabled: boolean; tts: boolean }> | null = null;
/** enabled: the API has a chat key (the Ask button hides otherwise); tts: the server voice is set up. Cached for the session. */
export const chatStatus = () => (chatOn ??= get('/api/chat/status', undefined, 8000).then((b) => ({ enabled: !!b?.enabled, tts: !!b?.tts })).catch(() => ({ enabled: false, tts: false })));
/** One question. Returns the answer, or throws an Error whose message is safe to show (the API's own wording). */
export async function askChat(body: { question: string; history: ChatTurn[]; field_id: string | null; screen: string; date: string; water_limit?: number | null }): Promise<string> {
  const ctl = new AbortController();
  const h = setTimeout(() => ctl.abort(), 40000);
  try {
    const r = await fetch(`${API_BASE}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal });
    const b = await r.json().catch(() => null);
    if (!r.ok) throw new Error(typeof b?.detail === 'string' ? b.detail : 'The assistant could not answer. Please try again.');
    return String(b?.answer ?? '');
  } catch (e) {
    if (e instanceof Error && e.name === 'AbortError') throw new Error('The assistant took too long. Please try again.');
    throw e instanceof Error ? e : new Error('The assistant could not answer. Please try again.');
  } finally { clearTimeout(h); }
}

// ---------- the grower's current rotation ----------
/** Make `todayId` the current rotation ("today") when the grower picked one; the satellite-detected one keeps `detected`. */
export function withToday(ss: RotationStrategy[], todayId?: string | null): RotationStrategy[] {
  const pick = todayId && ss.some((s) => s.id === todayId) ? todayId : null;
  return ss.map((s) => ({ ...s, detected: s.detected ?? s.is_baseline, is_baseline: pick ? s.id === pick : s.detected ?? s.is_baseline }));
}
const TODAY_KEY = 'croplytics.today';
/** The grower's picks, remembered in this browser (per field id). */
export function loadTodayPicks(): Record<string, string> { try { return JSON.parse(localStorage.getItem(TODAY_KEY) ?? '{}'); } catch { return {}; } }
export function saveTodayPicks(v: Record<string, string>) { try { localStorage.setItem(TODAY_KEY, JSON.stringify(v)); } catch { /* private mode */ } }
