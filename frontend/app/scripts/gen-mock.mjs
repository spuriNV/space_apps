// Generates the illustrative mock data in src/mock/*.json (deterministic).
// Shapes follow planner-spec.md B3 (Location, RotationStrategy, NewsItem, SourcedNumber).
// Real, cited facts (events, dates, URLs, rotation names, FAO-56 values) are copied from the spec.
// Everything else is illustrative and is flagged "method": "assumed" / "mock": true.
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'mock');
mkdirSync(OUT, { recursive: true });
const write = (name, obj) => writeFileSync(join(OUT, name), JSON.stringify(obj, null, 1));

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const r2 = (v) => Math.round(v * 100) / 100;
const MOCK_SRC = { id: 'mock', title: 'Illustrative mock value (frontend prototype)', url: null, accessed: '2026-11-14', verified: false };
const sn = (value, low, high, unit, method = 'assumed', source = MOCK_SRC, note = '') => ({ value, low, high, unit, method, source, note });

const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

// ---------- geometry ----------
function fieldGeom(lat, lon, widthM, heightM) {
  const mLat = 111320, mLon = 111320 * Math.cos((lat * Math.PI) / 180);
  const cols = Math.round(widthM / 30), rows = Math.round(heightM / 30);
  const dLon = 30 / mLon, dLat = 30 / mLat;
  const west = lon - (cols * dLon) / 2, south = lat - (rows * dLat) / 2;
  const ring = [
    [west, south], [west + cols * dLon, south], [west + cols * dLon, south + rows * dLat], [west, south + rows * dLat], [west, south],
  ].map((p) => p.map((v) => +v.toFixed(6)));
  return { cols, rows, dLon, dLat, west, south, ring };
}

function cellGrid(g, seed, lowCorner) {
  const rand = rng(seed);
  // smooth spatial field from a few random blobs
  const blobs = Array.from({ length: 7 }, () => ({ x: rand(), y: rand(), a: rand() * 2 - 1, s: 0.15 + rand() * 0.25 }));
  const features = [];
  for (let r = 0; r < g.rows; r++) {
    for (let c = 0; c < g.cols; c++) {
      const x = (c + 0.5) / g.cols, y = (r + 0.5) / g.rows;
      let v = 0;
      for (const b of blobs) v += b.a * Math.exp(-((x - b.x) ** 2 + (y - b.y) ** 2) / (2 * b.s * b.s));
      v = clamp(v / 1.6 + (rand() - 0.5) * 0.25, -1, 1);
      const dl = Math.hypot(x - lowCorner[0], y - lowCorner[1]);
      const low = clamp(1 - dl / 0.9 + (rand() - 0.5) * 0.08, 0, 1); // 1 = lowest-lying corner
      const edge = r === 0 || c === 0 || r === g.rows - 1 || c === g.cols - 1;
      const w = g.west + c * g.dLon, s = g.south + r * g.dLat;
      const f6 = (n) => +n.toFixed(6);
      features.push({
        type: 'Feature',
        properties: { id: r * g.cols + c, r, c, v: r2(v), low: r2(low), edge },
        geometry: { type: 'Polygon', coordinates: [[[f6(w), f6(s)], [f6(w + g.dLon), f6(s)], [f6(w + g.dLon), f6(s + g.dLat)], [f6(w), f6(s + g.dLat)], [f6(w), f6(s)]]] },
      });
    }
  }
  return { cell_m: 30, rows: g.rows, cols: g.cols, crs: 'EPSG:4326', grid_source: 'HLS 30 m (MGRS tile grid, illustrative alignment)', type: 'FeatureCollection', features };
}

// ---------- calendars (36 dekads per year) ----------
// classes: b bare, p partial, c covered, w water, u unknown
function riceYear(year) {
  const cls = Array(36).fill('b');
  const set = (a, b, k) => { for (let d = a; d <= b; d++) cls[d] = k; };
  if (year === 2022) {
    // fallow year (drought): bare all year, some weeds in spring
    set(8, 12, 'p');
    set(34, 35, 'w'); // late Dec 2022 storms begin
    return cls;
  }
  const late = year === 2023 ? 2 : year === 2019 || year === 2017 ? 1 : 0;
  const winterFloodStart = !(year === 2021); // no water for decomposition flood after 2021 harvest
  const winterFloodJan = !(year === 2022);
  if (winterFloodJan) set(0, year === 2023 ? 8 : 5, 'w');
  set(11 + late, 13 + late, 'w'); // flood-up and water seeding
  set(14 + late, 15 + late, 'p');
  set(16 + late, 25 + late, 'c');
  set(26 + late, 26 + late, 'p');
  if (winterFloodStart) set(30 + Math.min(late, 2), 35, 'w');
  return cls;
}
function forageYear(year) {
  const cls = Array(36).fill('c');
  const set = (a, b, k) => { for (let d = a; d <= b; d++) cls[d] = k; };
  if (year === 2020) {
    // double-crop year: small-grain silage then silage corn, alfalfa re-seeded in Oct
    set(11, 12, 'b'); set(13, 14, 'p'); set(25, 28, 'b'); set(29, 33, 'p');
    return cls;
  }
  set(0, 2, 'p'); set(34, 35, 'p'); // winter dormancy
  for (const d of [7, 10, 13, 16, 19, 22, 25, 28]) cls[d] = 'p'; // regrowth after each cut
  if (year === 2023) {
    set(9, 17, 'w'); // edge of the 2023 Tulare Lake flood extent (illustrative)
    set(18, 22, 'b'); set(23, 26, 'p'); set(27, 28, 'b'); set(29, 32, 'p');
  }
  if (year === 2022) { cls[23] = 'p'; cls[24] = 'p'; } // deficit-irrigated summer
  return cls;
}

function buildCalendar(locId, yearFn, seed, cdl, pTrans) {
  const rand = rng(seed);
  const years = [];
  let disagree = 0, valid = 0;
  for (const year of YEARS) {
    const truth = yearFn(year);
    const rule = [...truth], ml = [...truth];
    const ndvi = [], et = [];
    for (let d = 0; d < 36; d++) {
      const winter = d <= 5 || d >= 32;
      // cloud gaps > 30 days are left unknown (spec B5.1)
      if (winter && rand() < (year === 2017 || year === 2019 || year === 2023 ? 0.3 : 0.14)) { rule[d] = 'u'; ml[d] = 'u'; }
      const prev = truth[Math.max(0, d - 1)], next = truth[Math.min(35, d + 1)];
      const transition = prev !== truth[d] || next !== truth[d];
      if (rule[d] !== 'u') {
        valid++;
        const p = transition ? pTrans : year === 2022 ? 0.07 : 0.015;
        if (rand() < p) {
          disagree++;
          const alt = { b: 'p', p: rand() < 0.5 ? 'b' : 'c', c: 'p', w: 'b' }[truth[d]];
          if (rand() < 0.5) rule[d] = alt; else ml[d] = alt;
        }
      }
      const season = Math.sin(((d - 9) / 36) * 2 * Math.PI); // peaks mid-July
      const k = truth[d];
      const base = k === 'c' ? 0.62 + 0.2 * Math.max(0, season) : k === 'p' ? 0.28 : k === 'w' ? 0.03 : 0.14;
      ndvi.push(r2(clamp(base + (rand() - 0.5) * 0.06, -0.05, 0.92)));
      const eto = 3.6 + 3.1 * season; // mm/day, illustrative Central Valley curve
      const kc = k === 'c' ? 1.15 : k === 'p' ? 0.7 : k === 'w' ? 1.05 : 0.15;
      et.push(r2(clamp(eto * kc + (rand() - 0.5) * 0.4, 0.1, 9.5)));
    }
    const firstC = truth.indexOf('c');
    const lastC = truth.lastIndexOf('c');
    years.push({
      year, cdl: cdl[year], rule: rule.join(''), ml: ml.join(''), ndvi, et_mm_day: et,
      greenup_dekad: firstC >= 0 && locId === 'car_colusa_rice' ? firstC : null,
      senescence_dekad: lastC >= 0 && locId === 'car_colusa_rice' ? lastC + 1 : null,
      risks: [],
    });
  }
  return { location_id: locId, dekads_per_year: 36, classes: { b: 'bare', p: 'partial', c: 'covered', w: 'water', u: 'unknown' },
    thresholds: { bare_ndvi_lt: 0.2, partial_ndvi: [0.2, 0.35], covered_ndvi_gt: 0.35, water: 'NDWI > 0.3 or SCL 6 / DSWx', note: 'U rule of thumb (spec B5.1)' },
    detector_agreement_pct: sn(Math.round(100 - (100 * disagree) / valid), null, null, '%', 'computed', MOCK_SRC, 'share of valid dekads where rule and ML agree'),
    years };
}

function addRisks(cal, list) {
  for (const [year, dekad, type, label] of list) cal.years.find((y) => y.year === year).risks.push({ dekad, type, label });
}

// ---------- regional series (360 dekads) ----------
function series(yearVals, seed, amp, seasonal = 0) {
  const rand = rng(seed);
  const out = [];
  for (let i = 0; i < 360; i++) {
    const yf = i / 36 - 0.5; // year-centre anchored
    const y0 = clamp(Math.floor(yf), 0, 9), y1 = clamp(y0 + 1, 0, 9);
    const t = clamp(yf - y0, 0, 1);
    const base = yearVals[y0] * (1 - t) + yearVals[y1] * t;
    const s = seasonal * Math.cos(((i % 36) / 36) * 2 * Math.PI);
    out.push(Math.round(clamp(base + s + (rand() - 0.5) * amp, 1, 99)));
  }
  return out;
}
function regional(locId, smapYears, graceYears, wellYears, seed) {
  const smap = series(smapYears, seed, 10, 6);
  // early-2023 atmospheric rivers: soil profile fills quickly
  for (let i = 7 * 36; i < 7 * 36 + 12; i++) smap[i] = clamp(88 + ((i * 7) % 9), 1, 99);
  for (let i = 6 * 36 + 30; i < 7 * 36; i++) smap[i] = clamp(20 + (i - (6 * 36 + 30)) * 12, 1, 95);
  const grace = series(graceYears, seed + 1, 4, 0).map((v, i) => {
    const y = 2016 + Math.floor(i / 36), d = i % 36;
    // real gap between GRACE (ended 2017) and GRACE-FO (first data mid-2018)
    if ((y === 2017 && d >= 18) || (y === 2018 && d <= 15)) return null;
    return v;
  });
  const rand = rng(seed + 2);
  const imerg = Array.from({ length: 360 }, (_, i) => {
    const y = 2016 + Math.floor(i / 36), d = i % 36;
    const wet = d <= 8 || d >= 30 ? 1 : d <= 11 || d >= 28 ? 0.35 : 0.03;
    const yr = { 2016: 0.9, 2017: 1.8, 2018: 0.7, 2019: 1.5, 2020: 0.6, 2021: 0.45, 2022: 0.5, 2023: 2.1, 2024: 1.1, 2025: 0.9 }[y];
    let mm = wet * yr * (8 + rand() * 30);
    if (y === 2023 && (d <= 1 || (d >= 6 && d <= 7))) mm = 95 + rand() * 40;
    if (y === 2022 && d === 35) mm = 80;
    if (y === 2021 && d === 29) mm = 85; // 24 Oct 2021 atmospheric river
    return Math.round(mm);
  });
  return {
    location_id: locId,
    smap_rootzone_pct: { dataset: 'SPL4SMGP.008', label: 'Root-zone soil moisture percentile', native_scale: '9 km', unit: 'percentile', mock: true, values: smap },
    grace_gw_pct: { dataset: 'GRACE / GRACE-FO DA drought indicator', label: 'Groundwater storage percentile', native_scale: '0.25° grid (~28 km); underlying signal ~300 km', unit: 'percentile', mock: true, gap_note: 'No data Jul 2017 to May 2018: gap between the GRACE and GRACE-FO missions', values: grace },
    imerg_mm_dekad: { dataset: 'GPM IMERG Final daily', label: 'Rain in the 10-day period', native_scale: '0.1° (~10 km)', unit: 'mm', mock: true, values: imerg },
    dwr_well_depth_m: { dataset: 'DWR periodic groundwater levels (nearest wells)', label: 'Depth to water', unit: 'm', mock: true, years: YEARS, values: wellYears },
    heatwave_days: { dataset: 'NASA POWER T2M_MAX', label: 'Heatwave days per year (3+ days at 35 °C / 95 °F or more)', unit: 'days', mock: true, years: YEARS, values: YEARS.map((y, i) => Math.round(18 + i * 1.3 + (rng(seed + y)() - 0.5) * 12 + (y === 2020 || y === 2022 ? 9 : 0))) },
    modis_ndvi_anom: { dataset: 'MOD13Q1.061', label: 'May–Sept greenness anomaly', native_scale: '250 m', unit: 'σ', mock: true, years: YEARS, values: YEARS.map((y) => r2(({ 2021: -0.6, 2022: -2.1, 2023: -0.3, 2017: 0.5, 2019: 0.4 }[y] ?? 0.1) + (rng(seed + y * 3)() - 0.5) * 0.4)) },
  };
}

// ---------- locations ----------
const S = {
  nasa_eo_rice: { id: 'nasa_eo_rice_2022', title: 'NASA Earth Observatory: A Rough Year for Rice in California', url: 'https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/', verified: true },
  agalert_2023: { id: 'agalert_late_harvest', title: 'Ag Alert: Later rice harvest deals minor yield, quality impacts', url: 'https://www.agalert.com/california-ag-news/archives/january-3-2024/later-rice-harvest-deals-minor-yield-quality-impacts/', verified: true },
  nbc_tulare: { id: 'nbc_tulare_lake', title: 'NBC News: Dormant California lake reappeared and isn’t going anywhere fast', url: 'https://www.nbcnews.com/science/science-news/dormant-california-lake-reappeared-isnt-going-anywhere-fast-rcna92452', verified: true },
  swb_probation: { id: 'swrcb_tulare_probation', title: 'State Water Board press release: Tulare Lake Subbasin probationary hearing', url: 'https://water.waterboards.ca.gov/press_room/press_releases/2024/pr20240415-tulare-lake-probationary-hearing.html', verified: true },
  sjv_water: { id: 'sjvwater_ruling', title: 'SJV Water: Kings County judge rules against State Water Board', url: 'https://sjvwater.org/kings-county-judge-rules-against-state-water-board-in-high-stakes-groundwater-case', verified: true },
  farmprogress: { id: 'farmprogress_39yr', title: 'Farm Progress: Calif. rice acreage to drop to 39-year low', url: 'https://www.farmprogress.com/rice/calif-rice-acreage-to-drop-to-39-year-low', verified: true },
};

const gCar = fieldGeom(39.15, -122.1, 990, 600);
const gCaf = fieldGeom(36.2, -119.6, 570, 570);

const datasetsFor = () => ({
  power: { native_scale: '0.5° (~50 km)' }, imerg: { native_scale: '0.1° (~10 km)' }, smap_l3: { native_scale: '9 km' }, smap_l4: { native_scale: '9 km' },
  hls: { native_scale: '30 m' }, s2: { native_scale: '10 m' }, modis: { native_scale: '250 m' }, ecostress: { native_scale: '70 m' }, grace: { native_scale: '0.25°' },
  dem: { native_scale: '30 m' }, cdl: { native_scale: '30 m' }, openet: { native_scale: '30 m' }, cimis: {}, cdec: {}, dwr_wells: {}, rma: {}, usdm: {}, news: {},
});

const cdlCar = { 2016: 'Rice', 2017: 'Rice', 2018: 'Rice', 2019: 'Rice', 2020: 'Rice', 2021: 'Rice', 2022: 'Fallow/Idle', 2023: 'Rice', 2024: 'Rice', 2025: 'Rice (CDL pending)' };
const cdlCaf = { 2016: 'Alfalfa', 2017: 'Alfalfa', 2018: 'Alfalfa', 2019: 'Alfalfa', 2020: 'Winter wheat / Corn', 2021: 'Alfalfa', 2022: 'Alfalfa', 2023: 'Alfalfa (flooded Apr–Jun)', 2024: 'Alfalfa', 2025: 'Alfalfa (CDL pending)' };

const locations = [
  {
    id: 'car_colusa_rice', name: 'Colusa County rice check (example)', short_name: 'Colusa rice', valley: 'Sacramento Valley', region_adapter: 'ca', regime: 'drought_then_flood',
    state_fips: '06', county_fips: '011', ground_data: 'rich',
    geometry: { type: 'Polygon', coordinates: [gCar.ring] }, centroid: { lon: -122.1, lat: 39.15 },
    area_ha: sn(59.4, null, null, 'ha', 'computed', MOCK_SRC, 'example polygon; spec B1: 60 ha laser-levelled rice check (U)'), crs_working: 'EPSG:32610',
    soil: { mukey: 'mock', muname: 'Willows silty clay (illustrative)', drainage_class: 'Poorly drained', hydrologic_group: 'D', awc_mm_per_m: sn(150, 130, 170, 'mm/m'), om_pct: sn(2.4, 1.8, 3.0, '%'), texture_class: 'Silty clay', source: { id: 'ssurgo_sda', url: 'https://sdmdataaccess.sc.egov.usda.gov/', verified: false } },
    terrain: { slope_mean_pct: sn(0.1, 0, 0.2, '%'), slope_p90_pct: sn(0.2, 0.1, 0.3, '%'), elev_m: sn(24, 23, 25, 'm'), low_spot_fraction: sn(0.04, 0.02, 0.06, 'fraction'), note: 'Levelled field, slope zones not meaningful' },
    water: { source: 'surface', allocation_input: { unit: 'acre-ft/acre', value: 3.5 }, district: 'Glenn-Colusa ID (U)', sgma_subbasin: 'Colusa', sgma_status: { text: 'Colusa Subbasin: medium priority (U)', url: 'https://sgma.water.ca.gov/', verified: false }, cdec_stations: ['SHA', 'ORO'] },
    market_preference: 'sell',
    stations: [{ network: 'CIMIS', id: 250, name: 'Williams', distance_km: 8, years: [2016, 2026] }, { network: 'NOAA', id: 'U', name: 'Colusa / Williams (U station id)' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0 }, datasets: datasetsFor(), crop_history: cdlCar,
    observed_cover: { typically_bare_doy_ranges: [[290, 110]], years_used: YEARS, detector: 'consensus', summary: 'Bare mid-Oct to late Apr, except winter-flood years' },
    headline: 'Rice every year since 2016, fallowed in 2022.',
    events: [
      { date: '2022-05-01', type: 'drought_fallow', short: '2022 fallow', title: 'Sacramento Valley rice acreage roughly halved', detail: 'Colusa −84%, Glenn −75% vs 2021 (NASA Earth Observatory quoting UC Davis)', url: S.nasa_eo_rice.url, verified: true },
      { date: '2023-01-09', type: 'atmospheric_river', short: 'Jan–Mar 2023 atmospheric rivers', title: 'Jan–Mar 2023 atmospheric rivers', detail: 'Wet winter, late planting; harvest pushed into the rainy season (152 days planting-to-harvest vs 145–150 average)', url: S.agalert_2023.url, verified: true, end_date: '2023-03-20' },
    ],
  },
  {
    id: 'caf_tulare_forage', name: 'Tulare/Kings forage field for dairy (example)', short_name: 'Tulare/Kings forage', valley: 'San Joaquin Valley', region_adapter: 'ca', regime: 'groundwater_limit_then_flood',
    state_fips: '06', county_fips: '031', ground_data: 'rich',
    geometry: { type: 'Polygon', coordinates: [gCaf.ring] }, centroid: { lon: -119.6, lat: 36.2 },
    area_ha: sn(32.5, null, null, 'ha', 'computed', MOCK_SRC, 'example polygon; spec B1: 32 ha quarter-section (U)'), crs_working: 'EPSG:32610',
    soil: { mukey: 'mock', muname: 'Lethent silt loam (illustrative)', drainage_class: 'Moderately well drained', hydrologic_group: 'C', awc_mm_per_m: sn(165, 140, 180, 'mm/m'), om_pct: sn(1.1, 0.8, 1.5, '%'), texture_class: 'Silt loam', source: { id: 'ssurgo_sda', url: 'https://sdmdataaccess.sc.egov.usda.gov/', verified: false } },
    terrain: { slope_mean_pct: sn(0.2, 0.1, 0.4, '%'), slope_p90_pct: sn(0.5, 0.3, 0.7, '%'), elev_m: sn(66, 65, 68, 'm'), low_spot_fraction: sn(0.12, 0.08, 0.18, 'fraction'), note: 'Low south-west corner: ponding candidate (U)' },
    water: { source: 'groundwater', allocation_input: { unit: 'acre-ft/acre', value: 3.0 }, district: 'GSA allocation (your number)', sgma_subbasin: 'Tulare Lake', sgma_status: { text: 'Tulare Lake Subbasin placed on SGMA probation 16 Apr 2024; in litigation since', url: S.swb_probation.url, verified: true }, cdec_stations: ['PNF'] },
    market_preference: 'feed_own_herd',
    stations: [{ network: 'CIMIS', id: 15, name: 'Stratford (U)', distance_km: 14, years: [2016, 2026] }, { network: 'NOAA', id: 'U', name: 'Hanford (U station id)' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0 }, datasets: datasetsFor(), crop_history: cdlCaf,
    observed_cover: { typically_bare_doy_ranges: [], years_used: YEARS, detector: 'consensus', summary: 'Covered most of the year; short dips after each cutting' },
    headline: 'Alfalfa for dairy under a groundwater pumping limit.',
    events: [
      { date: '2022-07-01', type: 'drought_fallow', short: '2021–22 drought', title: '2021–22 drought and heavy pumping', detail: 'Groundwater-dependent forage; GRACE storage percentile at its lowest of the record shown', url: null, verified: false },
      { date: '2023-03-15', type: 'atmospheric_river', short: 'Spring 2023 Tulare Lake re-floods', title: 'Tulare Lake re-floods', detail: 'Peaked near 114,000 acres (46,000 ha) by DWR satellite measurement', url: S.nbc_tulare.url, verified: true, end_date: '2023-06-30' },
      { date: '2024-04-16', type: 'sgma_probation', short: 'Apr 2024 SGMA probation', title: 'Tulare Lake Subbasin placed on SGMA probation', detail: 'State Water Board action for subsidence from over-pumping; litigation since', url: S.swb_probation.url, verified: true },
    ],
  },
];
write('locations.json', locations);

write('cells.json', {
  car_colusa_rice: cellGrid(gCar, 11, [0.1, 0.1]),
  caf_tulare_forage: cellGrid(gCaf, 23, [0.0, 0.0]),
});

const calCar = buildCalendar('car_colusa_rice', riceYear, 101, cdlCar, 0.16);
addRisks(calCar, [
  [2017, 0, 'rain', 'Heavy rain'], [2017, 3, 'rain', 'Heavy rain'], [2017, 4, 'rain', 'Heavy rain'], [2019, 4, 'rain', 'Heavy rain'], [2019, 5, 'rain', 'Heavy rain'],
  [2021, 29, 'rain', 'Heavy rain (24 Oct 2021 storm)'], [2022, 35, 'rain', 'Heavy rain'], [2023, 0, 'rain', 'Atmospheric river'], [2023, 1, 'rain', 'Atmospheric river'], [2023, 6, 'rain', 'Atmospheric river'], [2023, 7, 'rain', 'Atmospheric river'], [2024, 3, 'rain', 'Heavy rain'],
  [2016, 34, 'frost', 'Frost'], [2018, 4, 'frost', 'Frost'], [2020, 35, 'frost', 'Frost'], [2022, 5, 'frost', 'Frost'], [2024, 1, 'frost', 'Frost'],
  [2017, 19, 'heat', 'Heatwave'], [2018, 20, 'heat', 'Heatwave'], [2020, 23, 'heat', 'Heatwave'], [2020, 24, 'heat', 'Heatwave'], [2021, 18, 'heat', 'Heatwave'], [2021, 19, 'heat', 'Heatwave'], [2022, 24, 'heat', 'Heatwave (Sept 2022)'], [2022, 20, 'heat', 'Heatwave'], [2023, 20, 'heat', 'Heatwave'], [2024, 18, 'heat', 'Heatwave'], [2024, 19, 'heat', 'Heatwave'], [2025, 21, 'heat', 'Heatwave'],
  ...[2021, 2022].flatMap((y) => [9, 12, 15, 18, 21, 27].map((d) => [y, d, 'dry', 'Dry spell (SMAP below 20th percentile)'])), [2020, 27, 'dry', 'Dry spell'], [2016, 9, 'dry', 'Dry spell'],
]);
const calCaf = buildCalendar('caf_tulare_forage', forageYear, 202, cdlCaf, 0.05);
addRisks(calCaf, [
  [2017, 1, 'rain', 'Heavy rain'], [2017, 4, 'rain', 'Heavy rain'], [2019, 3, 'rain', 'Heavy rain'], [2023, 0, 'rain', 'Atmospheric river'], [2023, 1, 'rain', 'Atmospheric river'], [2023, 6, 'rain', 'Atmospheric river'], [2023, 7, 'rain', 'Atmospheric river'], [2024, 4, 'rain', 'Heavy rain'],
  [2016, 35, 'frost', 'Frost'], [2018, 5, 'frost', 'Frost'], [2019, 0, 'frost', 'Frost'], [2022, 1, 'frost', 'Frost'], [2025, 0, 'frost', 'Frost'],
  ...[2016, 2017, 2018, 2019, 2021, 2023, 2025].map((y) => [y, 20, 'heat', 'Heatwave']), ...[2020, 2022, 2024].flatMap((y) => [19, 20, 23, 24].map((d) => [y, d, 'heat', 'Heatwave'])),
  ...[2021, 2022].flatMap((y) => [6, 9, 12, 15, 18, 21, 26, 30].map((d) => [y, d, 'dry', 'Dry spell (SMAP below 20th percentile)'])), [2020, 28, 'dry', 'Dry spell'], [2016, 12, 'dry', 'Dry spell'],
]);
write('calendar.json', { car_colusa_rice: calCar, caf_tulare_forage: calCaf });

write('regional.json', {
  car_colusa_rice: regional('car_colusa_rice', [42, 78, 46, 70, 30, 11, 8, 90, 62, 47], [26, 55, 46, 60, 40, 15, 6, 48, 56, 45], [9.1, 8.2, 8.6, 7.9, 9.0, 11.8, 13.9, 10.2, 9.4, 9.8], 301),
  caf_tulare_forage: regional('caf_tulare_forage', [38, 74, 40, 66, 27, 9, 7, 93, 58, 41], [9, 30, 21, 28, 15, 6, 2, 31, 26, 18], [52, 49, 51, 50, 55, 61, 68, 60, 59, 62], 401),
});

// ---------- strategies ----------
const SCORE_KEYS = ['water_use', 'forage_value', 'n_fixation', 'erosion', 'organic_matter', 'market', 'pest_break', 'infiltration', 'n_scavenging'];
const sc = (arr) => Object.fromEntries(SCORE_KEYS.map((k, i) => [k, sn(arr[i][0], arr[i][1], arr[i][2], 'score 0–100', 'model', MOCK_SRC, 'rule of thumb, not a model')]));
const FAO12 = { id: 'fao56_table12', title: 'FAO-56 Table 12', url: 'https://www.fao.org/4/x0490e/x0490e0b.htm', accessed: '2026-11-14', verified: true };
const EQIP = { program: 'USDA EQIP practice 340 Cover Crop', rate_per_acre_usd: { value: null, method: 'assumed' }, url: 'https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program', verified: false };

function strat(o) {
  const [I, Il, Ih] = o.irr;
  return {
    id: o.id, location_id: o.loc, name: o.name, short_name: o.short, is_baseline: !!o.base, cycle_years: o.cycle,
    calendar: o.calendar, calendar_months: o.months, month_cover: o.cover, allocation_rule: o.rule ?? null,
    exposure: {
      bare_days_per_year: sn(...o.bare, 'days'), exposed_rain_days: sn(...o.rain, 'days/yr'), exposed_frost_days: sn(...o.frost, 'days/yr'), exposed_heat_days: sn(...o.heat, 'days/yr'), exposed_dry_days: sn(...o.dry, 'days/yr'),
      replay: { 2022: { irrigation_need_mm: sn(...o.r22, 'mm'), exposed_rain_days: sn(o.rain[0] - 1, 0, o.rain[2], 'days'), note: o.r22n }, 2023: { irrigation_need_mm: sn(...o.r23, 'mm'), exposed_rain_days: sn(o.rain[0] * 2 + 1, o.rain[0], o.rain[2] * 2 + 3, 'days'), note: o.r23n } },
      scenario: { dT_c: 0, dP_pct: 0 }, cover_basis: o.base ? 'observed consensus cover' : 'modelled cover',
    },
    water: {
      etc_mm_season: sn(...o.etc, 'mm', 'computed', FAO12, 'Kc × ETo, FAO-56 single coefficient; ETo values are mock'),
      irrigation_need_mm: sn(I, Il, Ih, 'mm', 'computed', MOCK_SRC, 'I = Σ max(0, ETc − 0.8 P); rice adds flood-establishment term (U)'),
      etc_by_month_mm: o.etcm,
      openet_et_mm_season: o.openet ? sn(...o.openet, 'mm', 'measured', { id: 'openet', title: 'OpenET ensemble (mock value)', url: 'https://openetdata.org/', accessed: '2026-11-14', verified: false }) : null,
      etc_vs_openet_pct: o.openet ? sn(Math.round((100 * (o.etc[0] - o.openet[0])) / o.openet[0]), null, null, '%', 'computed') : null,
    },
    scores: sc(o.scores), composite: { ...sn(...o.comp, 'score 0–100', 'model'), weights_used: { water_use: 3, forage_value: 2, n_fixation: 1, erosion: 2, organic_matter: 2, market: 3 } },
    risk_profile: { rma_share_drought: sn(...o.rma[0], 'share'), rma_share_excess_moisture: sn(...o.rma[1], 'share'), rma_share_heat: sn(...o.rma[2], 'share'), rma_years: [2010, 2024], crop: o.rmaCrop, note: 'insurance history, not a forecast' },
    funding: o.cover340 ? [EQIP] : [],
    brief: { why: o.why.map((text) => ({ text, source_ids: ['mock'], numbers_used: [], author: 'template', checked: true })), local_review: o.review.map(([item, severity]) => ({ item, severity })), explainer_cards: o.cards ?? [], llm_report: { sentences: o.why.length, numbers_checked: 0, rejected: 0, model: 'template (mock)', cached_at: null } },
    uncertainty: { agronomic_gap_count: o.gaps, detector_disagreement_pct: 7 },
  };
}
// month cover class per month for the mini calendar strips: b/p/c/w
const strategies = [
  strat({ id: 'car0_continuous_rice', loc: 'car_colusa_rice', name: 'Continuous rice, winter flood', short: 'Rice + winter flood', base: true, cycle: 1,
    calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }],
    months: ['winter flood', 'drain', 'field prep', 'flood, water-seed', 'rice', 'rice', 'rice', 'rice', 'drain, harvest', 'straw, re-flood', 'winter flood', 'winter flood'], cover: 'wwbwpcccpbww',
    bare: [58, 40, 75], rain: [3, 1, 6], frost: [2, 0, 4], heat: [0, 0, 1], dry: [4, 1, 9], irr: [1300, 1150, 1500], etc: [1010, 930, 1090], openet: [1060, 980, 1140],
    etcm: [35, 45, 30, 95, 150, 185, 210, 180, 110, 40, 30, 30], r22: [1420, 1260, 1620], r22n: 'Allocation cut: this plan could not be watered in 2022', r23: [1180, 1040, 1350], r23n: 'Late planting; harvest ran into October rain',
    scores: [[28, 18, 38], [0, 0, 0], [0, 0, 0], [55, 42, 66], [52, 42, 61], [78, 62, 90], [10, 5, 18], [30, 20, 40], [20, 10, 32]], comp: [52, 44, 60],
    rma: [[0.62, 0.5, 0.72], [0.21, 0.14, 0.3], [0.05, 0.02, 0.08]], rmaCrop: 'Rice, Colusa County', gaps: 2,
    why: ['This is what the field does now: rice May to October, then a winter flood to break down straw.', 'It uses the most water of the four plans and depends on a full surface allocation.'],
    review: [['Irrigation need is above the allocation you entered', 'high'], ['Waterfowl habitat and straw-management obligations', 'medium']] }),
  strat({ id: 'car1_rice_wintercover', loc: 'car_colusa_rice', name: 'Rice + winter cover (no winter flood)', short: 'Rice + winter cover', cycle: 1, cover340: true,
    calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 1, crop_id: 'cereal_vetch_cover', plant: '10-25', terminate: '03-20', role: 'cover', timing_source: 'assumed (U)' }],
    months: ['cover', 'cover', 'terminate, prep', 'flood, seed', 'rice', 'rice', 'rice', 'rice', 'harvest', 'drill cover', 'cover', 'cover'], cover: 'ccbwpcccpbpc',
    bare: [34, 20, 52], rain: [1, 0, 3], frost: [1, 0, 2], heat: [0, 0, 1], dry: [2, 0, 6], irr: [1100, 960, 1280], etc: [1040, 950, 1130], openet: null,
    etcm: [40, 55, 45, 95, 150, 185, 210, 180, 110, 35, 30, 30], r22: [1210, 1060, 1400], r22n: 'Cover crop would still have grown on winter rain', r23: [1000, 880, 1160], r23n: 'Cover held the soil through the Jan–Mar storms',
    scores: [[42, 30, 53], [12, 5, 22], [38, 20, 55], [74, 60, 85], [70, 58, 80], [70, 52, 84], [48, 34, 60], [58, 44, 70], [66, 50, 80]], comp: [61, 50, 70],
    rma: [[0.62, 0.5, 0.72], [0.21, 0.14, 0.3], [0.05, 0.02, 0.08]], rmaCrop: 'Rice, Colusa County', gaps: 3, cards: ['cover_crop', 'nitrogen_fixing'],
    why: ['A cereal and vetch cover replaces the winter flood, so the field is not bare or ponded through the heavy-rain months.', 'It saves the winter-flood water, and vetch adds some nitrogen.'],
    review: [['Cover-crop species and seeding after rice are unverified (UC trials under way)', 'high'], ['Straw decomposition without a winter flood', 'high'], ['Waterfowl habitat obligations', 'medium'], ['Herbicide carryover to the cover crop', 'medium']] }),
  strat({ id: 'car2_dry_year_plan', loc: 'car_colusa_rice', name: 'Dry-year plan: fallow with cover or safflower when allocation < 50%', short: 'Dry-year plan', cycle: 1, cover340: true, rule: 'Applies in years when the surface allocation is under 50%',
    calendar: [{ year: 1, crop_id: 'safflower', plant: '04-05', harvest: '08-10', role: 'cash', timing_source: 'fao56_table11 Safflower April California (V)' }],
    months: ['cover / bare', 'cover / bare', 'plant safflower', 'safflower', 'safflower', 'safflower', 'harvest', 'bare', 'bare', 'bare', 'bare', 'bare'], cover: 'ppbpccpbbbbb',
    bare: [150, 110, 190], rain: [5, 2, 9], frost: [3, 1, 5], heat: [6, 3, 10], dry: [12, 6, 20], irr: [420, 330, 540], etc: [520, 450, 600], openet: null,
    etcm: [25, 30, 45, 80, 120, 110, 50, 15, 12, 10, 12, 11], r22: [470, 370, 600], r22n: 'Built for a year like 2022: a crop on about a third of rice water', r23: [330, 250, 430], r23n: 'Not the plan for a wet year: field sits bare from August',
    scores: [[82, 72, 90], [0, 0, 0], [8, 0, 18], [38, 24, 52], [40, 28, 52], [46, 28, 64], [72, 58, 84], [50, 36, 62], [18, 8, 30]], comp: [57, 43, 68],
    rma: [[0.48, 0.3, 0.64], [0.12, 0.05, 0.22], [0.14, 0.06, 0.24]], rmaCrop: 'Safflower, Colusa County', gaps: 4, cards: ['drought_tolerant', 'deep_rooting'],
    why: ['When the allocation is under half, a deep-rooted safflower crop or a cover uses about a third of the water rice needs.', 'The field is bare from August, so autumn and winter rain exposure goes up.'],
    review: [['Safflower market and contract nearby', 'high'], ['Heavy clay rice soil: drainage for a dryland crop', 'high'], ['Herbicide carryover from rice', 'medium']] }),
  strat({ id: 'car3_rice_winter_wheat', loc: 'car_colusa_rice', name: 'Rice–winter wheat', short: 'Rice–winter wheat', cycle: 2,
    calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 2, crop_id: 'winter_wheat', plant: '11-20', harvest: '06-15', role: 'cash', timing_source: 'fao56_table11 Winter wheat December California (V)' }],
    months: ['wheat', 'wheat', 'wheat', 'wheat', 'heading', 'harvest', 'bare', 'bare', 'bare', 'bare', 'drill wheat', 'wheat'], cover: 'pccccpbbbbbp',
    bare: [96, 70, 125], rain: [2, 0, 4], frost: [1, 0, 3], heat: [5, 2, 9], dry: [7, 3, 12], irr: [780, 650, 930], etc: [760, 680, 850], openet: null,
    etcm: [40, 60, 95, 120, 110, 45, 15, 14, 12, 12, 20, 30], r22: [860, 720, 1020], r22n: 'Wheat year needs little irrigation; rice year still exposed to cuts', r23: [690, 570, 830], r23n: 'Wheat stood in water during the Jan–Mar storms',
    scores: [[60, 50, 70], [10, 4, 18], [0, 0, 0], [68, 56, 78], [58, 48, 68], [80, 68, 90], [34, 24, 44], [48, 36, 60], [56, 42, 70]], comp: [66, 58, 73],
    rma: [[0.55, 0.42, 0.68], [0.24, 0.15, 0.34], [0.06, 0.02, 0.1]], rmaCrop: 'Rice and wheat, Colusa County', gaps: 2,
    why: ['Wheat grows on winter rain in alternate years, roughly halving irrigation need across the two-year cycle.', 'Both crops are grasses, so the pest and weed break is modest.'],
    review: [['Wheat on a levelled rice check: winter drainage', 'high'], ['Herbicide carryover between rice and wheat', 'medium']] }),

  strat({ id: 'caf0_alfalfa', loc: 'caf_tulare_forage', name: 'Alfalfa, 7–8 cuts, 4–5 year stand', short: 'Alfalfa (baseline)', base: true, cycle: 5,
    calendar: [{ year: 1, crop_id: 'alfalfa_hay', plant: '09-25', harvest: 'cuts Mar–Oct', role: 'forage', timing_source: 'uc_alfalfa (V window)' }],
    months: ['dormant / slow', 'growth', 'cut 1', 'cut 2', 'cut 3', 'cut 4', 'cut 5', 'cut 6', 'cut 7', 'cut 8', 'slow', 'dormant'], cover: 'pccccccccccp',
    bare: [8, 2, 18], rain: [0, 0, 1], frost: [0, 0, 1], heat: [0, 0, 1], dry: [1, 0, 3], irr: [1350, 1200, 1500], etc: [1380, 1260, 1500], openet: [1290, 1200, 1390],
    etcm: [35, 55, 95, 130, 170, 195, 210, 185, 140, 95, 45, 25], r22: [1480, 1320, 1640], r22n: 'All of it pumped in a year like 2022', r23: [1150, 1000, 1300], r23n: 'Stand lost where water stood for weeks',
    scores: [[22, 12, 32], [92, 82, 98], [88, 76, 96], [84, 74, 92], [76, 66, 85], [72, 56, 84], [30, 20, 40], [74, 62, 84], [30, 18, 42]], comp: [55, 47, 63],
    rma: [[0.44, 0.3, 0.58], [0.2, 0.1, 0.32], [0.18, 0.1, 0.28]], rmaCrop: 'Alfalfa / forage, Tulare and Kings Counties', gaps: 1,
    why: ['This is what the field does now: alfalfa cut seven or eight times a year for four to five years.', 'It gives the most feed and fixes its own nitrogen, and it needs the most pumped water.'],
    review: [['Irrigation need is above the allocation you entered', 'high'], ['SGMA status: Tulare Lake Subbasin probation (16 Apr 2024), in litigation', 'high']] }),
  strat({ id: 'caf1_smallgrain_corn', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + silage corn', short: 'Small grain + corn', cycle: 1,
    calendar: [{ year: 1, crop_id: 'small_grain_silage', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'silage_corn', plant: '05-10', harvest: '09-01', role: 'forage', timing_source: 'assumed (U)' }],
    months: ['wheat / triticale', 'growth', 'growth', 'harvest silage', 'plant corn', 'corn', 'corn', 'corn harvest', 'bare', 'drill small grain', 'grain', 'grain'], cover: 'ccccbpccbbpc',
    bare: [62, 45, 80], rain: [1, 0, 2], frost: [0, 0, 1], heat: [2, 0, 4], dry: [5, 2, 9], irr: [1000, 880, 1150], etc: [1090, 990, 1200], openet: null,
    etcm: [40, 60, 95, 85, 70, 150, 215, 170, 45, 20, 25, 35], r22: [1100, 960, 1260], r22n: 'Summer corn carries most of the pumping', r23: [860, 740, 1000], r23n: 'Winter grain used the rain; corn planted late',
    scores: [[46, 34, 56], [90, 78, 97], [0, 0, 0], [62, 50, 72], [56, 46, 66], [84, 70, 94], [14, 8, 22], [44, 32, 56], [70, 56, 82]], comp: [58, 48, 66],
    rma: [[0.38, 0.26, 0.52], [0.22, 0.12, 0.34], [0.2, 0.1, 0.3]], rmaCrop: 'Corn silage, Tulare and Kings Counties', gaps: 3,
    why: ['Two silage crops a year: the winter one grows mostly on rain, the summer corn on pumped water.', 'High feed output with less water than alfalfa, but no nitrogen fixation and a bare gap in September.'],
    review: [['Silage corn and small-grain timing unverified (typical SJV double crop)', 'medium'], ['Nitrogen budget without a legume', 'medium'], ['SGMA status: probation, in litigation', 'high']] }),
  strat({ id: 'caf2_smallgrain_sorghum', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + sorghum-sudan', short: 'Small grain + sorghum-sudan', cycle: 1,
    calendar: [{ year: 1, crop_id: 'small_grain_silage', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'sorghum_sudan', plant: '05-10', harvest: 'cuts Jun–Aug', role: 'forage', timing_source: 'fao56_table11 Sudan (V stage lengths)' }],
    months: ['grain', 'growth', 'growth', 'harvest', 'plant sorghum-sudan', 'cut 1', 'cut 2', 'cut 3', 'terminate', 'drill grain', 'grain', 'grain'], cover: 'ccccbpcccbpc',
    bare: [48, 32, 66], rain: [1, 0, 2], frost: [0, 0, 1], heat: [1, 0, 3], dry: [4, 1, 8], irr: [760, 640, 900], etc: [880, 790, 980], openet: null,
    etcm: [40, 60, 95, 85, 55, 110, 150, 135, 60, 20, 25, 35], r22: [840, 710, 990], r22n: 'Lowest pumping of the forage plans in a dry year', r23: [640, 530, 770], r23n: 'Winter grain used the rain',
    scores: [[64, 52, 74], [72, 58, 84], [0, 0, 0], [66, 54, 76], [60, 50, 70], [70, 54, 84], [16, 8, 24], [52, 40, 64], [72, 58, 84]], comp: [64, 55, 72],
    rma: [[0.4, 0.26, 0.54], [0.2, 0.1, 0.32], [0.16, 0.08, 0.26]], rmaCrop: 'Forage sorghum, Tulare and Kings Counties', gaps: 4, cards: ['drought_tolerant'],
    why: ['Sorghum-sudan replaces corn as the summer forage and needs less water (a widely stated extension position, to be cited).', 'Feed quality is lower than corn silage, so the ration needs a nutritionist’s review.'],
    review: [['Sorghum-sudan water saving vs corn needs a UC ANR or NRCS citation', 'high'], ['Feed quality and ration balance for the dairy', 'high'], ['SGMA status: probation, in litigation', 'high']] }),
  strat({ id: 'caf3_short_alfalfa_break', loc: 'caf_tulare_forage', name: 'Shorter alfalfa stand + winter-cereal break + unirrigated summer', short: 'Short alfalfa + break', cycle: 4, cover340: true,
    calendar: [{ year: 1, crop_id: 'alfalfa_hay', plant: '09-25', harvest: 'cuts Mar–Oct, 3 yr', role: 'forage', timing_source: 'uc_alfalfa (V window)' }, { year: 4, crop_id: 'winter_cereal_silage', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }],
    months: ['cereal', 'cereal', 'cereal', 'harvest silage', 'fallow (no pumping)', 'fallow', 'fallow', 'prep', 're-seed alfalfa', 'establishing', 'establishing', 'dormant'], cover: 'cccpbbbbbppp',
    bare: [44, 28, 62], rain: [0, 0, 2], frost: [0, 0, 1], heat: [6, 3, 10], dry: [9, 4, 15], irr: [980, 850, 1120], etc: [1060, 950, 1170], openet: null,
    etcm: [35, 50, 85, 75, 20, 15, 14, 14, 40, 60, 40, 25], r22: [1060, 920, 1220], r22n: 'A break year placed in 2022 would have meant no summer pumping', r23: [820, 700, 950], r23n: 'Cereal break used the wet winter',
    scores: [[48, 36, 58], [74, 60, 86], [64, 50, 78], [66, 52, 78], [64, 54, 74], [66, 48, 80], [58, 44, 70], [62, 50, 74], [54, 40, 68]], comp: [62, 51, 70],
    rma: [[0.44, 0.3, 0.58], [0.2, 0.1, 0.32], [0.18, 0.1, 0.28]], rmaCrop: 'Alfalfa / forage, Tulare and Kings Counties', gaps: 3, cards: ['nitrogen_fixing', 'deep_rooting'],
    why: ['Take alfalfa out after three years, grow a winter cereal on rain, and leave the field unirrigated for one summer before re-seeding.', 'One summer in four has no pumping; that summer the field is bare in the heat.'],
    review: [['Feed gap in the break summer', 'high'], ['Dust and weeds on an unirrigated summer field', 'medium'], ['SGMA status: probation, in litigation', 'high']] }),
];
write('strategies.json', strategies);

// ---------- news ----------
write('news.json', {
  car_colusa_rice: [
    { date: '2022-05-01', title: 'A Rough Year for Rice in California', source: 'NASA Earth Observatory', url: S.nasa_eo_rice.url, rank: 1, place_match: ['Sacramento Valley', 'Colusa'], query_id: 'car_2022_drought', verified: true, date_note: 'event date from spec; publication date to confirm', signal: { dataset: 'smap_l4', label: 'SMAP root-zone soil moisture', value_pct: 8, lead_days: null } },
    { date: '2022-05-20', title: 'Calif. rice acreage to drop to 39-year low', source: 'Farm Progress', url: S.farmprogress.url, rank: 2, place_match: ['Sacramento Valley'], query_id: 'car_2022_drought', verified: true, signal: { dataset: 'smap_l3', label: 'SMAP soil moisture', value_pct: 9, lead_days: null } },
    { date: '2023-01-09', title: 'Atmospheric-river storms, Jan–Mar 2023 (headline to be cached)', source: 'News cache pending', url: null, rank: 3, place_match: ['Sacramento Valley'], query_id: 'car_2023_flood', verified: false, signal: { dataset: 'imerg', label: 'IMERG 3-day rain', value_pct: 97, lead_days: null } },
    { date: '2024-01-03', title: 'Later rice harvest deals minor yield, quality impacts', source: 'Ag Alert', url: S.agalert_2023.url, rank: 2, place_match: ['Sacramento Valley'], query_id: 'car_2023_flood', verified: true, signal: { dataset: 'hls', label: 'HLS green-up date', value_pct: null, lead_days: null } },
  ],
  caf_tulare_forage: [
    { date: '2023-03-15', title: 'Dormant California lake reappeared and isn’t going anywhere fast', source: 'NBC News', url: S.nbc_tulare.url, rank: 3, place_match: ['Tulare Lake', 'Kings County'], query_id: 'caf_2023_flood', verified: true, date_note: 'event date; publication date to confirm', signal: { dataset: 'imerg', label: 'IMERG 3-day rain', value_pct: 98, lead_days: null } },
    { date: '2024-04-16', title: 'State Water Board places Tulare Lake Subbasin on probation', source: 'State Water Resources Control Board', url: S.swb_probation.url, rank: 1, place_match: ['Tulare Lake Subbasin'], query_id: 'caf_2024_probation', verified: true, signal: { dataset: 'grace', label: 'GRACE groundwater storage', value_pct: 26, lead_days: null } },
    { date: '2025-10-15', title: 'Kings County judge rules against State Water Board in high-stakes groundwater case', source: 'SJV Water', url: S.sjv_water.url, rank: 2, place_match: ['Kings County'], query_id: 'caf_2024_probation', verified: true, date_note: 'litigation timeline per spec; exact date to confirm', signal: { dataset: 'grace', label: 'GRACE groundwater storage', value_pct: 18, lead_days: null } },
  ],
});

// ---------- dataset catalogue (layers drawer) ----------
write('datasets.json', [
  { id: 'hls', name: 'HLS', long_name: 'Harmonized Landsat Sentinel-2', sees: 'Cover, greenness, open water', native_scale: '30 m', footprint_m: 30, cadence: '2–3 days', since: 2013, group: 'field', color: '#7ee081', in_stack: 'surface' },
  { id: 'ecostress', name: 'ECOSTRESS', long_name: 'ECOSTRESS on the Space Station', sees: 'Land-surface temperature, crop water use', native_scale: '70 m', footprint_m: 70, cadence: 'irregular', since: 2018, group: 'field', color: '#ffb454' },
  { id: 'modis', name: 'MODIS', long_name: 'MODIS vegetation indices (MOD13Q1)', sees: 'Greenness history since 2000', native_scale: '250 m', footprint_m: 250, cadence: '16 days', since: 2000, group: 'field', color: '#c3e88d' },
  { id: 'smap', name: 'SMAP', long_name: 'Soil Moisture Active Passive (L3 / L4)', sees: 'Surface and root-zone soil moisture', native_scale: '9 km', footprint_m: 9000, cadence: 'daily', since: 2015, group: 'regional', color: '#5ab0ff', in_stack: 'soil' },
  { id: 'imerg', name: 'IMERG', long_name: 'GPM IMERG precipitation', sees: 'Rain and storms', native_scale: '~10 km', footprint_m: 10000, cadence: 'daily', since: 2000, group: 'regional', color: '#9d8cff' },
  { id: 'grace', name: 'GRACE', long_name: 'GRACE / GRACE-FO drought indicators', sees: 'Groundwater storage percentile', native_scale: '0.25°', footprint_m: 27800, cadence: 'weekly', since: 2003, group: 'regional', color: '#ff7eb6', in_stack: 'groundwater', caveat: 'Underlying signal is about 300 km wide' },
]);

write('bc.json', {
  title: 'Why not BC yet',
  intro: 'The idea started in British Columbia: the August 2023 Salmon River forage-water orders and the November 2021 Sumas Prairie flood. The ground data there is too thin to check a field-level answer, so the tool is built and tested in California first.',
  lines: [
    { label: 'No OpenET', text: 'Field-scale measured crop water use covers western US states only.' },
    { label: 'No field-soil API', text: 'BC soil comes from survey polygons or a 250 m global model.' },
    { label: 'One station per valley', text: 'Salmon Arm CS is the only active daily weather station in its valley.' },
    { label: 'Crop labels since 2011', text: 'AAFC crop inventory starts in 2011, with thin BC ground sampling in 2021.' },
  ],
  limit: 'BC is out of scope; transferability is a claim to test.',
  places: [{ name: 'Salmon River / Shuswap', lat: 50.62, lon: -119.33 }, { name: 'Sumas Prairie', lat: 49.06, lon: -122.17 }],
  news: [
    { date: '2023-08-16', title: 'Fish population protection orders: about 398 licence holders told to stop watering forage crops', source: 'BC Gov News', url: 'https://news.gov.bc.ca/releases/2023FOR0052-001305', verified: true },
    { date: '2021-11-15', title: 'Catastrophic flooding hits Fraser Valley', source: 'Country Life in BC', url: 'https://www.countrylifeinbc.com/catastrophic-flooding-hits-fraser-valley/', verified: true },
  ],
  next_step: { label: 'Next step: BC appendix', ref: 'planner-spec.md, Appendix A' },
});

console.log('mock written to', OUT);
