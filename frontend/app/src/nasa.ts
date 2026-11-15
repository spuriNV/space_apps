// The NASA datasets behind a field, in the grower's words. NASA sources are listed first everywhere in the app.
// Status comes from GET /api/locations/{id} `nasa_datasets` when the API sends it; otherwise from FALLBACK below.
// FALLBACK is the single switch to flip by hand when a dataset goes live without an API field for it.

export type NasaStatus = 'live' | 'saved' | 'example' | 'pending';
// note: an `items` entry may carry `note`; we keep the app's own plain-language text instead
export interface NasaDataset {
  id: string; name: string; agency: string; tells: string; scale: string; usedFor: string; status: NasaStatus; note?: string;
}

/** Status as of 14 Nov 2026. live = on screen from real data; saved = downloaded, not on screen yet;
 *  example = the screen shows example numbers; pending = not downloaded yet. */
export const FALLBACK: Record<string, NasaStatus> = {
  hls: 'saved', landsat: 'live', power: 'live', smap: 'example', grace: 'example', imerg: 'saved',
  opera: 'saved', modis: 'pending', ecostress: 'pending', nasadem: 'saved', iss: 'live',
};

export const NASA_CATALOGUE: Omit<NasaDataset, 'status'>[] = [
  { id: 'hls', name: 'Harmonized Landsat Sentinel-2 (HLS)', agency: 'NASA / USGS', tells: 'Whether the field is bare, green or flooded, every 2 to 3 days.', scale: '100 ft squares (30 m)', usedFor: 'Field calendar' },
  { id: 'landsat', name: 'Landsat 8 and 9', agency: 'NASA / USGS', tells: 'Green cover and bare ground on this field since 2016.', scale: '100 ft squares (30 m)', usedFor: 'Field calendar, green cover' },
  { id: 'power', name: 'NASA POWER weather', agency: 'NASA Langley', tells: 'Daily sun, wind and humidity, which set how much water a crop uses.', scale: 'one reading for about 35 miles (0.5°)', usedFor: 'Crop water use' },
  { id: 'smap', name: 'SMAP soil moisture', agency: 'NASA JPL', tells: 'Whether the root zone is wetter or drier than usual for the date.', scale: 'one reading for a 6-mile square (9 km)', usedFor: 'Soil moisture answer, 3D view' },
  { id: 'grace', name: 'GRACE-FO groundwater', agency: 'NASA / GFZ', tells: 'Whether groundwater in the basin is above or below usual. Basin-wide, not your own well.', scale: 'one reading for a 17-mile square (0.25°)', usedFor: 'Groundwater answer, 3D view' },
  { id: 'imerg', name: 'GPM IMERG rainfall', agency: 'NASA / JAXA', tells: 'Daily rain over the field, filling the gaps between weather stations.', scale: 'one reading for a 6-mile square (0.1°)', usedFor: 'Rain check against stations' },
  { id: 'opera', name: 'OPERA surface water', agency: 'NASA JPL', tells: 'When the field held standing water after rain or irrigation.', scale: '100 ft squares (30 m)', usedFor: 'Flooded days in the calendar' },
  { id: 'modis', name: 'MODIS greenness', agency: 'NASA', tells: 'How green the area was against normal, back to 2000.', scale: '800 ft squares (250 m)', usedFor: 'Long-term greenness' },
  { id: 'ecostress', name: 'ECOSTRESS', agency: 'NASA JPL, on the Space Station', tells: 'Crop water stress from leaf temperature.', scale: '230 ft squares (70 m)', usedFor: 'Crop stress' },
  { id: 'nasadem', name: 'NASADEM elevation', agency: 'NASA JPL', tells: 'Slope, and low spots where water ponds or frost settles.', scale: '100 ft squares (30 m)', usedFor: 'Slope and low spots' },
  { id: 'iss', name: 'Astronaut photos from the ISS', agency: 'NASA Johnson Space Center', tells: 'What the valley around the field looked like from orbit.', scale: 'photo, about 400 mm lens', usedFor: 'Photo on this panel' },
];

export const STATUS_WORDS: Record<NasaStatus, string> = {
  live: 'Live.',
  saved: 'Downloaded; not on screen yet.',
  example: 'Example numbers on screen until it is wired in.',
  pending: 'Not downloaded yet.',
};

const RANK: Record<NasaStatus, number> = { pending: 0, example: 1, saved: 2, live: 3 };
const ALIAS: Record<string, string> = { smap_l3: 'smap', smap_l4: 'smap', dem: 'nasadem', iss: 'iss', hls: 'hls', landsat: 'landsat', smap: 'smap', grace: 'grace', imerg: 'imerg', modis: 'modis', ecostress: 'ecostress', power: 'power', nasadem: 'nasadem', opera: 'opera', dswx: 'opera', opera_dswx: 'opera', gpm_imerg: 'imerg', grace_fo: 'grace', nasa_power: 'power', iss_photos: 'iss', s2: '', cdl: '', cdec: '', usdm: '', news: '', openet: '', cimis: '', dwr_wells: '', rma: '' };
function toStatus(s: unknown): NasaStatus | null {
  const v = String(s ?? '').toLowerCase();
  if (!v) return null;
  if (['live', 'real', 'served', 'on_screen'].includes(v)) return 'live';
  if (['saved', 'cached', 'downloaded', 'fetched', 'computed'].includes(v)) return 'saved';
  if (['example', 'fixture', 'mock'].includes(v)) return 'example';
  return 'pending';
}

/** Build the list. `apiNasa` = location.nasa_datasets (array or object), `datasets` = location.datasets (backend fetch status),
 *  `used` = what this screen actually shows from real data (upgrades to live). */
export function nasaList(apiNasa: unknown, datasets: Record<string, { status?: string }> | undefined, used: Partial<Record<string, NasaStatus>>): { list: NasaDataset[]; fromApi: boolean } {
  const status: Record<string, NasaStatus> = { ...FALLBACK };
  // backend fetch status: "real" there means downloaded, not necessarily on screen
  for (const [k, v] of Object.entries(datasets ?? {})) {
    const id = ALIAS[k] ?? k;
    if (id && status[id] && v?.status === 'real' && RANK[status[id]] < RANK.saved && status[id] !== 'example') status[id] = 'saved';
  }
  let fromApi = false;
  const items: { id?: string; key?: string; status?: string; note?: string; [k: string]: unknown }[] = Array.isArray(apiNasa)
    ? apiNasa : apiNasa && typeof apiNasa === 'object' ? Object.entries(apiNasa as Record<string, object>).map(([id, v]) => ({ id, ...(v as object) })) : [];
  const seen: Record<string, NasaStatus> = {};
  for (const it of items) {
    const raw = String(it.id ?? it.key ?? '').toLowerCase(), id = ALIAS[raw] ?? raw;
    let st = toStatus(it.status);
    if (!id || !st || !(id in FALLBACK)) continue;
    fromApi = true;
    // the API's "live" means the data is downloaded and served; it is on screen only where this app uses it
    if (st === 'live' && FALLBACK[id] !== 'live') st = 'saved';
    if (!seen[id] || RANK[st] > RANK[seen[id]]) seen[id] = st; // several API entries can map to one dataset (SMAP L3 and L4)
  }
  Object.assign(status, seen);
  for (const [id, st] of Object.entries(used)) if (st && RANK[st] > RANK[status[id] ?? 'pending']) status[id] = st;
  const list = NASA_CATALOGUE.map((d) => ({ ...d, status: status[d.id] ?? 'pending' }));
  // live first, then example, saved, pending; catalogue order inside each group
  const ORDER: Record<NasaStatus, number> = { live: 0, example: 1, saved: 2, pending: 3 };
  list.sort((a, b) => ORDER[a.status] - ORDER[b.status]);
  return { list, fromApi };
}
