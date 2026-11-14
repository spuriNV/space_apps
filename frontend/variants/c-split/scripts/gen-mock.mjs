// Generates src/mock/*.json, shaped like the planner-spec B3 schemas.
// All numbers are ILLUSTRATIVE (method "assumed", verified false) unless they are
// cited facts copied from planner-spec.md (dates, events, URLs).
// Run: npm run mock
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const out = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'mock');
mkdirSync(out, { recursive: true });
const ACCESSED = '2026-11-14';

// ---------- deterministic random ----------
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

// ---------- sources (URLs copied from planner-spec.md) ----------
const SOURCES = {
  mock: { id: 'mock', title: 'Illustrative mock value (frontend prototype)', url: null, verified: false },
  fao56_table11: { id: 'fao56_table11', title: 'FAO-56 Table 11, crop stage lengths', url: 'https://www.fao.org/4/x0490e/x0490e0b.htm', verified: true },
  fao56_table12: { id: 'fao56_table12', title: 'FAO-56 Table 12, crop coefficients (Kc)', url: 'https://www.fao.org/4/x0490e/x0490e0b.htm', verified: true },
  uc_rice_blog: { id: 'uc_rice_blog', title: 'UC Rice Blog: planting and harvest timing', url: 'https://www.ucanr.edu/blog/uc-rice-blog', verified: true },
  uc_alfalfa: { id: 'uc_alfalfa', title: 'UC Alfalfa: Irrigated Alfalfa Management', url: 'https://alfalfa.ucdavis.edu/IrrigatedAlfalfa', verified: true },
  nasa_eo_rice_2022: { id: 'nasa_eo_rice_2022', title: 'NASA Earth Observatory: A Rough Year for Rice in California', url: 'https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/', verified: true },
  farmprogress_2022: { id: 'farmprogress_2022', title: 'Farm Progress: Calif. rice acreage to drop to 39-year low', url: 'https://www.farmprogress.com/rice/calif-rice-acreage-to-drop-to-39-year-low', verified: true },
  agalert_2024: { id: 'agalert_2024', title: 'Ag Alert: Later rice harvest deals minor yield, quality impacts', url: 'https://www.agalert.com/california-ag-news/archives/january-3-2024/later-rice-harvest-deals-minor-yield-quality-impacts/', verified: true },
  nbc_tulare_2023: { id: 'nbc_tulare_2023', title: 'NBC News: Dormant California lake reappeared', url: 'https://www.nbcnews.com/science/science-news/dormant-california-lake-reappeared-isnt-going-anywhere-fast-rcna92452', verified: true },
  swrcb_probation_2024: { id: 'swrcb_probation_2024', title: 'State Water Board: Tulare Lake Subbasin probationary hearing', url: 'https://water.waterboards.ca.gov/press_room/press_releases/2024/pr20240415-tulare-lake-probationary-hearing.html', verified: true },
  sjvwater_2024: { id: 'sjvwater_2024', title: 'SJV Water: Kings County judge rules against State Water Board', url: 'https://sjvwater.org/kings-county-judge-rules-against-state-water-board-in-high-stakes-groundwater-case', verified: true },
  nrcs_eqip: { id: 'nrcs_eqip', title: 'USDA NRCS EQIP, practice 340 Cover Crop', url: 'https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program', verified: false },
  rma_col: { id: 'rma_col', title: 'USDA RMA cause-of-loss, 2010–2024', url: 'https://www.rma.usda.gov/tools-reports/summary-business/cause-loss', verified: false },
  openet: { id: 'openet', title: 'OpenET 30 m evapotranspiration (ensemble)', url: 'https://openetdata.org/', verified: false },
  ssurgo_sda: { id: 'ssurgo_sda', title: 'USDA SSURGO via Soil Data Access', url: 'https://sdmdataaccess.sc.egov.usda.gov/', verified: true },
  cimis: { id: 'cimis', title: 'CIMIS weather stations', url: 'https://cimis.water.ca.gov/Stations.aspx', verified: true },
  cdl: { id: 'cdl', title: 'USDA NASS Cropland Data Layer', url: 'https://www.nass.usda.gov/Research_and_Science/Cropland/Release/', verified: false },
  hls: { id: 'hls', title: 'NASA Harmonized Landsat Sentinel-2 (HLS) 30 m', url: 'https://planetarycomputer.microsoft.com/api/stac/v1', verified: false },
  power: { id: 'power', title: 'NASA POWER daily meteorology', url: 'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M', verified: false },
  imerg: { id: 'imerg', title: 'NASA GPM IMERG daily precipitation', url: 'https://registry.opendata.aws/nasa-gpm3imergdf/', verified: false },
  ndvi_usgs: { id: 'ndvi_usgs', title: 'USGS: NDVI, the foundation for remote sensing phenology', url: 'https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology', verified: true },
  covercrop_selector: { id: 'covercrop_selector', title: 'Western Cover Crop Selector', url: 'https://covercrop-selector.org', verified: false },
};
const src = (id) => ({ ...SOURCES[id], accessed: ACCESSED });
const sn = (value, low, high, unit, sourceId = 'mock', method = 'assumed', note = '') => ({
  value, unit, low, high, method, source: src(sourceId), note,
});

// ---------- geometry helpers ----------
const M_PER_DEG = 111320;
function fieldGeometry(lon, lat, widthM, heightM, notch) {
  const dLon = (m) => m / (M_PER_DEG * Math.cos((lat * Math.PI) / 180));
  const dLat = (m) => m / M_PER_DEG;
  const cols = Math.round(widthM / 30);
  const rows = Math.round(heightM / 30);
  const x0 = lon - dLon(widthM / 2);
  const y0 = lat - dLat(heightM / 2);
  const p = (c, r) => [+(x0 + dLon(c * 30)).toFixed(6), +(y0 + dLat(r * 30)).toFixed(6)];
  // notch: a farmstead / pump yard cut from one corner (cells), so the block is not a perfect rectangle
  const inside = (c, r) => !(c >= cols - notch.c && r >= rows - notch.r);
  const ring = [p(0, 0), p(cols, 0), p(cols, rows - notch.r), p(cols - notch.c, rows - notch.r), p(cols - notch.c, rows), p(0, rows), p(0, 0)];
  return { cols, rows, p, inside, polygon: { type: 'Polygon', coordinates: [ring] }, dLon, dLat };
}

function buildCells(preset, geo, kind) {
  const r = rng(preset === 'car_colusa_rice' ? 11 : 29);
  const feats = [];
  const { cols, rows } = geo;
  // stress hotspot centre (cells)
  const hot = kind === 'rice' ? { c: cols * 0.72, r: rows * 0.3, rad: 5.5 } : { c: cols * 0.22, r: rows * 0.7, rad: 4.5 };
  for (let row = 0; row < rows; row++) {
    for (let c = 0; c < cols; c++) {
      if (!geo.inside(c, row)) continue;
      const smooth = 0.05 * Math.sin(c / 4.1 + 1.3) * Math.cos(row / 3.3) + 0.035 * Math.sin((c + row) / 6.5);
      const noise = (r() - 0.5) * 0.05;
      let ndvi;
      if (kind === 'rice') {
        // levee lines between rice checks every 8 columns; inlet side slightly thinner stand
        const levee = c % 8 === 0 ? -0.2 : 0;
        ndvi = 0.74 + smooth + noise + levee - 0.04 * (row / rows);
      } else {
        // alfalfa: irrigation borders cut on a rolling schedule -> bands at different regrowth
        const band = Math.floor(row / 4) % 3;
        ndvi = [0.78, 0.6, 0.42][band] + smooth + noise;
      }
      const d = Math.hypot(c - hot.c, row - hot.r);
      const hotFactor = Math.max(0, 1 - d / hot.rad);
      ndvi -= 0.3 * hotFactor;
      ndvi = Math.min(0.92, Math.max(0.12, ndvi));
      const et = Math.max(1.2, 1.6 + 6.4 * ndvi + (r() - 0.5) * 0.6 - 1.2 * hotFactor); // mm/day, July
      const lst = +(-(ndvi - 0.68) * 9 + 3.2 * hotFactor + (r() - 0.5) * 0.8).toFixed(1); // K vs field median
      const hotspot = lst > 2.0 && ndvi < 0.55;
      feats.push({
        type: 'Feature',
        id: feats.length + 1,
        properties: {
          id: feats.length + 1, row, col: c,
          ndvi: +ndvi.toFixed(2), et_mm_day: +et.toFixed(1), lst_anom_k: lst,
          cover_class: ndvi < 0.2 ? 'bare' : ndvi < 0.35 ? 'partial' : 'covered',
          stress_hotspot: hotspot,
        },
        geometry: { type: 'Polygon', coordinates: [[geo.p(c, row), geo.p(c + 1, row), geo.p(c + 1, row + 1), geo.p(c, row + 1), geo.p(c, row)]] },
      });
    }
  }
  return feats;
}

function smapCell(lon, lat, offE, offN) {
  // 9 km EASE-Grid 2.0 cell containing the field (offset so the field is not dead centre)
  const dLon = (m) => m / (M_PER_DEG * Math.cos((lat * Math.PI) / 180));
  const dLat = (m) => m / M_PER_DEG;
  const w = lon - dLon(4500 + offE), e = lon + dLon(4500 - offE), s = lat - dLat(4500 + offN), n = lat + dLat(4500 - offN);
  const f = (v) => +v.toFixed(5);
  return { type: 'Polygon', coordinates: [[[f(w), f(s)], [f(e), f(s)], [f(e), f(n)], [f(w), f(n)], [f(w), f(s)]]] };
}

// ---------- locations ----------
const carGeo = fieldGeometry(-122.1, 39.15, 990, 600, { c: 5, r: 4 });
const cafGeo = fieldGeometry(-119.6, 36.2, 810, 420, { c: 4, r: 3 });
const carCells = buildCells('car_colusa_rice', carGeo, 'rice');
const cafCells = buildCells('caf_tulare_forage', cafGeo, 'alfalfa');

const datasets = (extra = {}) => ({
  power: { resolution: '0.5° × 0.625°', footprint_km: 50 }, imerg: { resolution: '0.1°', footprint_km: 10 },
  smap_l3: { resolution: '9 km EASE-Grid 2.0', footprint_km: 9 }, hls: { resolution: '30 m', footprint_km: 0.03 },
  s2: { resolution: '10 m', footprint_km: 0.01 }, modis: { resolution: '250 m', footprint_km: 0.25 },
  ecostress: { resolution: '70 m', footprint_km: 0.07 }, grace: { resolution: '~300 km signal', footprint_km: 300 },
  openet: { resolution: '30 m', footprint_km: 0.03 }, ...extra,
});

const locations = [
  {
    id: 'car_colusa_rice',
    name: 'Colusa County rice check (example)',
    short_name: 'Colusa rice',
    region_label: 'Sacramento Valley · west of Williams',
    region_adapter: 'ca', regime: 'drought_then_flood', state_fips: '06', county_fips: '011',
    ground_data: 'rich',
    current_crop: 'Rice (medium grain, water-seeded)',
    geometry: carGeo.polygon,
    centroid: { lon: -122.1, lat: 39.15 },
    area_ha: sn(+(carCells.length * 0.09).toFixed(1), 58, 62, 'ha', 'mock', 'assumed', 'Example field; drag to your own'),
    crs_working: 'EPSG:32610',
    soil: { mukey: 'mock', muname: 'Willows silty clay (illustrative)', drainage_class: 'Poorly drained', hydrologic_group: 'D', awc_mm_per_m: sn(150, 130, 170, 'mm/m'), om_pct: sn(2.4, 1.8, 3.0, '%'), texture_class: 'Silty clay', source: src('ssurgo_sda') },
    terrain: { slope_mean_pct: sn(0.1, 0, 0.2, '%'), slope_p90_pct: sn(0.2, 0.1, 0.3, '%'), elev_m: sn(21, 20, 22, 'm'), low_spot_fraction: sn(0.02, 0, 0.05, 'fraction'), note: 'Laser-levelled field: slope zones not meaningful.' },
    water: { source: 'surface', allocation_input: { unit: 'acre-ft/acre', value: 4.0 }, district: 'Glenn-Colusa ID (U)', sgma_subbasin: 'Colusa', sgma_status: { text: 'Colusa Subbasin, medium priority (to confirm)', url: null, verified: false }, cdec_stations: ['SHA', 'ORO'] },
    market_preference: 'sell',
    stations: [{ network: 'CIMIS', id: 250, name: 'Williams', distance_km: 8, years: [2016, 2026] }, { network: 'NOAA', id: 'U', name: 'Colusa/Williams (station id to confirm)' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0, footprint: smapCell(-122.1, 39.15, 1800, -1200) },
    datasets: datasets(),
    crop_history: { 2016: 'Rice', 2017: 'Rice', 2018: 'Rice', 2019: 'Rice', 2020: 'Rice', 2021: 'Rice', 2022: 'Fallow/Idle', 2023: 'Rice', 2024: 'Rice', 2025: 'Rice' },
    observed_cover: { typically_bare_doy_ranges: [[290, 110]], years_used: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], detector: 'consensus', summary: 'Bare mid-Oct to late Apr, except winter-flood years' },
    events: [
      { date: '2022-05-01', type: 'drought_fallow', title: 'Sacramento Valley rice acreage roughly halved', url: SOURCES.nasa_eo_rice_2022.url, verified: true },
      { date: '2023-01-09', type: 'atmospheric_river', title: 'Jan–Mar 2023 atmospheric rivers; late planting and harvest', url: null, verified: false },
    ],
    headline: { bare_window: 'mid-Oct → late Apr', detector_agreement_pct: 93, cells_30m: carCells.length },
    grid: { cols: carGeo.cols, rows: carGeo.rows, cell_m: 30 },
  },
  {
    id: 'caf_tulare_forage',
    name: 'Tulare/Kings dairy forage field (example)',
    short_name: 'Tulare/Kings forage',
    region_label: 'San Joaquin Valley · between Corcoran and Hanford',
    region_adapter: 'ca', regime: 'groundwater_cap_then_flood', state_fips: '06', county_fips: '031',
    ground_data: 'rich',
    current_crop: 'Alfalfa hay, 7–8 cuts',
    geometry: cafGeo.polygon,
    centroid: { lon: -119.6, lat: 36.2 },
    area_ha: sn(+(cafCells.length * 0.09).toFixed(1), 30, 34, 'ha', 'mock', 'assumed', 'Example field; drag to your own'),
    crs_working: 'EPSG:32610',
    soil: { mukey: 'mock', muname: 'Lethent silt loam (illustrative)', drainage_class: 'Moderately well drained', hydrologic_group: 'C', awc_mm_per_m: sn(140, 120, 160, 'mm/m'), om_pct: sn(1.1, 0.8, 1.5, '%'), texture_class: 'Silt loam', source: src('ssurgo_sda') },
    terrain: { slope_mean_pct: sn(0.2, 0.1, 0.4, '%'), slope_p90_pct: sn(0.4, 0.2, 0.6, '%'), elev_m: sn(62, 61, 63, 'm'), low_spot_fraction: sn(0.04, 0.01, 0.08, 'fraction'), note: 'Nearly flat: 3D view shows data values, not terrain.' },
    water: { source: 'groundwater', allocation_input: { unit: 'acre-ft/acre', value: 2.5 }, district: 'GSA allocation (your input)', sgma_subbasin: 'Tulare Lake', sgma_status: { text: 'Tulare Lake Subbasin placed on probation, 16 Apr 2024 (in litigation; status changes)', url: SOURCES.swrcb_probation_2024.url, verified: true }, cdec_stations: ['PNF'] },
    market_preference: 'feed_own_herd',
    stations: [{ network: 'CIMIS', id: 15, name: 'Stratford (to confirm)', distance_km: 19, years: [2016, 2026] }, { network: 'NOAA', id: 'U', name: 'Hanford (station id to confirm)' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0, footprint: smapCell(-119.6, 36.2, -1500, 2100) },
    datasets: datasets(),
    crop_history: { 2016: 'Alfalfa', 2017: 'Alfalfa', 2018: 'Alfalfa', 2019: 'Corn', 2020: 'Winter wheat / corn', 2021: 'Alfalfa', 2022: 'Alfalfa', 2023: 'Alfalfa', 2024: 'Alfalfa', 2025: 'Alfalfa' },
    observed_cover: { typically_bare_doy_ranges: [[265, 300]], years_used: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], detector: 'consensus', summary: 'Covered most of the year; bare only at re-seeding' },
    events: [
      { date: '2022-07-01', type: 'drought_pumping', title: '2021–22 drought and heavy groundwater pumping', url: null, verified: false },
      { date: '2023-03-15', type: 'flood', title: 'Tulare Lake re-floods (~114,000 acres at peak)', url: SOURCES.nbc_tulare_2023.url, verified: true },
      { date: '2024-04-16', type: 'sgma_probation', title: 'Tulare Lake Subbasin placed on SGMA probation', url: SOURCES.swrcb_probation_2024.url, verified: true },
    ],
    headline: { bare_window: 'late Sept → Oct (re-seed years)', detector_agreement_pct: 95, cells_30m: cafCells.length },
    grid: { cols: cafGeo.cols, rows: cafGeo.rows, cell_m: 30 },
  },
];

const bc = {
  id: 'bc_not_yet', title: 'Why not BC yet',
  lines: ['No OpenET: nothing to check modelled crop water use against', 'No field-scale soil API (no SSURGO equivalent)', 'About one weather station per valley', 'Crop labels only since 2011'],
  next_step: 'Transferability to BC is a claim to test, not a result.',
  centroid: { lon: -119.3, lat: 50.7 },
};

// ---------- strategies ----------
// month states: w water, b bare, p partial, c covered
const cal = (states, labels) => states.split('').map((s, i) => ({ month: i + 1, state: s, label: labels[i] }));
const AF_MM = 304.8;

function strategy(o) {
  const mk = (v) => sn(v[0], v[1], v[2], 'score 0–100', 'mock', 'model');
  const scale = (v, f, add = 0) => v.map((x) => Math.max(0, Math.round(x * f + add)));
  return {
    id: o.id, location_id: o.loc, name: o.name, short: o.short, is_baseline: !!o.baseline, cycle_years: o.cycle ?? 1,
    year_shown: o.yearShown ?? null,
    tagline: o.tagline,
    calendar: o.events,
    month_strip: cal(o.strip, o.labels),
    month_strip_source: o.stripSource,
    allocation_rule: o.allocRule ?? null,
    exposure: {
      bare_days_per_year: sn(...o.bare, 'days'),
      exposed_rain_days: sn(...o.rain, 'days/yr', 'imerg', 'model', 'Days with heavy rain (≥ 25–50 mm) while the field is less than half covered and not flooded'),
      exposed_frost_days: sn(...o.frost, 'days/yr', 'power', 'model'),
      exposed_heat_days: sn(...o.heat, 'days/yr', 'power', 'model'),
      replay: {
        2022: { exposed_rain_days: sn(...scale(o.rain, 0.35), 'days'), irrigation_need_mm: sn(...scale(o.irr, 1.12), 'mm') },
        2023: { exposed_rain_days: sn(...scale(o.rain, 2.4, 2), 'days'), irrigation_need_mm: sn(...scale(o.irr, 0.88), 'mm') },
      },
      scenario: { dT_c: 0, dP_pct: 0 },
      cover_basis: o.baseline ? 'observed consensus cover (HLS / Sentinel-2)' : 'modelled cover from the crop calendar',
    },
    water: {
      etc_mm_season: sn(...scale(o.irr, 0.86, 60), 'mm', 'fao56_table12', 'model'),
      irrigation_need_mm: sn(...o.irr, 'mm', 'fao56_table12', 'model'),
      openet_et_mm_season: o.openet ? sn(...o.openet, 'mm', 'openet', 'measured') : null,
      etc_vs_openet_pct: o.openetPct != null ? sn(o.openetPct, o.openetPct - 6, o.openetPct + 6, '%', 'openet', 'computed') : null,
    },
    scores: {
      water_use: mk(o.s.water), forage_value: mk(o.s.forage), n_fixation: mk(o.s.nfix), erosion: mk(o.s.erosion),
      organic_matter: mk(o.s.om), market: mk(o.s.market), pest_break: mk(o.s.pest), infiltration: mk(o.s.infil), n_scavenging: mk(o.s.nscav),
    },
    risk_profile: {
      rma_share_drought: sn(o.rma[0], null, null, '%', 'rma_col'), rma_share_excess_moisture: sn(o.rma[1], null, null, '%', 'rma_col'),
      rma_share_heat: sn(o.rma[2], null, null, '%', 'rma_col'), rma_share_other: sn(o.rma[3], null, null, '%', 'rma_col'),
      rma_years: [2010, 2024], rma_label: o.rmaLabel,
    },
    funding: o.funding ? [{ program: 'USDA EQIP practice 340 Cover Crop', rate_per_acre_usd: { value: null, low: null, high: null, unit: 'USD/acre', method: 'assumed', source: src('nrcs_eqip'), note: 'Payment rate not yet confirmed; ask the local NRCS office' }, url: SOURCES.nrcs_eqip.url, verified: false }] : [],
    brief: o.brief,
    uncertainty: { agronomic_gap_count: o.brief.gaps.length, detector_disagreement_pct: o.loc === 'car_colusa_rice' ? 7 : 5 },
  };
}

const sent = (text, source_ids, numbers_used = [], author = 'llm') => ({ text, source_ids, numbers_used, author, checked: true });
const RICE_REVIEW = [
  { item: 'Straw decomposition without winter flooding', severity: 'high' },
  { item: 'Waterfowl habitat obligations and programme contracts', severity: 'high' },
  { item: 'Herbicide carryover to rotation or cover crops', severity: 'medium' },
  { item: 'Weedy rice and rice water weevil pressure', severity: 'medium' },
  { item: 'District rules on water transfers and fallowing', severity: 'low' },
];
const FORAGE_REVIEW = [
  { item: 'Irrigation need exceeds the allocation you entered', severity: 'high' },
  { item: 'SGMA status of the Tulare Lake Subbasin (in litigation; changes)', severity: 'high' },
  { item: 'Ration balance and silage pit capacity with the nutritionist', severity: 'medium' },
  { item: 'Equipment for chopping small-grain and sorghum silage', severity: 'medium' },
  { item: 'Nitrate and prussic-acid risk in drought-stressed sorghum-sudan', severity: 'low' },
];
const L = {
  car0: ['winter flood', 'drain', 'field prep', 'flood, water-seed', 'rice', 'rice', 'rice', 'rice', 'drain, harvest', 'straw, re-flood', 'winter flood', 'winter flood'],
  car1: ['cover', 'cover', 'terminate, prep', 'flood, seed', 'rice', 'rice', 'rice', 'rice', 'harvest', 'drill cover', 'cover', 'cover'],
  car2: ['cover / bare', 'cover / bare', 'plant safflower', 'safflower', 'safflower', 'safflower', 'harvest', 'bare', 'bare', 'bare', 'bare', 'bare'],
  car3: ['wheat', 'wheat', 'wheat', 'wheat', 'heading', 'harvest', 'bare', 'bare', 'bare', 'bare', 'drill wheat', 'wheat'],
  caf0: ['dormant', 'growth', 'cut 1', 'cut 2', 'cut 3', 'cut 4', 'cut 5', 'cut 6', 'cut 7', 'cut 8', 'slow', 'dormant'],
  caf1: ['wheat / triticale', 'growth', 'growth', 'harvest silage', 'plant corn', 'corn', 'corn', 'corn harvest', 'bare', 'drill small grain', 'grain', 'grain'],
  caf2: ['grain', 'growth', 'growth', 'harvest', 'plant sorghum-sudan', 'cut 1', 'cut 2', 'cut 3', 'terminate', 'drill grain', 'grain', 'grain'],
  caf3: ['cereal', 'cereal', 'cereal', 'harvest silage', 'fallow, no pumping', 'fallow', 'fallow', 'prep', 're-seed alfalfa', 'establishing', 'establishing', 'dormant'],
};

const strategies = [
  strategy({
    id: 'car0_continuous_rice', loc: 'car_colusa_rice', baseline: true, name: 'Continuous rice, winter flood', short: 'Rice + winter flood',
    tagline: 'What the field does today: rice every year, flooded over winter for straw and waterfowl.',
    events: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 1, crop_id: 'winter_flood', plant: '11-01', terminate: '02-10', role: 'water', timing_source: 'assumed (U)' }],
    strip: 'wbbwccccpbww', labels: L.car0, stripSource: 'uc_rice_blog',
    bare: [62, 45, 80], rain: [2, 0, 5], frost: [6, 3, 10], heat: [0, 0, 1], irr: [1340, 1190, 1500], openet: [1105, 1040, 1170], openetPct: 4,
    s: { water: [22, 15, 30], forage: [0, 0, 0], nfix: [0, 0, 0], erosion: [50, 40, 60], om: [48, 40, 57], market: [78, 65, 88], pest: [10, 5, 18], infil: [30, 22, 40], nscav: [20, 12, 30] },
    rma: [46, 31, 4, 19], rmaLabel: 'Colusa County · rice',
    brief: {
      why: [sent('This is the baseline every alternative is compared against: rice from May to early October, then a winter flood.', ['uc_rice_blog'], [], 'template')],
      evidence: [sent('Satellite cover shows rice in 9 of the last 10 years; 2022 was fallow.', ['cdl', 'nasa_eo_rice_2022'], ['9', '10', '2022'], 'template')],
      benefits: [], gaps: ['Rice flood and percolation water is an estimate until cited.'], local_review: RICE_REVIEW.slice(0, 3), explainer_cards: ['water_balance'],
      llm_report: { sentences: 2, numbers_checked: 4, rejected: 0, model: 'template only', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'car1_rice_wintercover', loc: 'car_colusa_rice', name: 'Rice + winter cover (no winter flood)', short: 'Rice + winter cover',
    tagline: 'Keep rice; drill a cereal/vetch cover after straw chop instead of re-flooding.',
    events: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 1, crop_id: 'cereal_vetch_cover', plant: '10-25', terminate: '03-20', role: 'cover', timing_source: 'assumed (U)' }],
    strip: 'ccpwccccppcc', labels: L.car1, stripSource: 'uc_rice_blog', funding: true,
    bare: [36, 20, 55], rain: [1, 0, 3], frost: [2, 0, 5], heat: [0, 0, 1], irr: [1120, 980, 1270], openet: [1105, 1040, 1170], openetPct: 4,
    s: { water: [36, 26, 46], forage: [8, 0, 16], nfix: [38, 22, 52], erosion: [71, 58, 82], om: [66, 55, 76], market: [72, 58, 84], pest: [24, 14, 35], infil: [52, 40, 63], nscav: [68, 55, 80] },
    rma: [46, 31, 4, 19], rmaLabel: 'Colusa County · rice',
    brief: {
      why: [
        sent('Your field is typically bare from mid-October to late April unless it is flooded, which is when the heaviest rain arrives.', ['hls'], ['mid-October', 'late April']),
        sent('A cereal/vetch cover drilled after straw chop keeps the soil covered through that window and cuts bare days from about 62 to about 36 a year.', ['hls', 'covercrop_selector'], ['62', '36']),
        sent('Skipping the winter flood lowers the season\'s irrigation need from roughly 1,340 mm to 1,120 mm (4.4 to 3.7 acre-ft/acre).', ['fao56_table12'], ['1,340', '1,120', '4.4', '3.7']),
        sent('Rice timing stays the same: half of fields are planted by 12 May on average, and harvest runs late September into October.', ['uc_rice_blog'], ['12 May']),
      ],
      evidence: [
        sent('Cover calendar 2016–2025: bare or unknown in 22–30 winter weeks of non-flood years; rule and ML detectors agree on 93% of weeks.', ['hls'], ['22', '30', '93']),
        sent('2022: the block was fallow all year, when Sacramento Valley rice acreage was roughly halved.', ['nasa_eo_rice_2022', 'farmprogress_2022'], ['2022']),
        sent('OpenET measured rice ET of about 1,105 mm for the season; our modelled crop water use is within 4% of it.', ['openet'], ['1,105', '4']),
        sent('Soil is poorly drained silty clay (hydrologic group D): expect a limited infiltration gain from any rotation.', ['ssurgo_sda'], []),
      ],
      benefits: [], gaps: ['Cover-crop species and seeding date after rice are not yet backed by a California trial result.', 'Rice flood and percolation water is an estimate until cited.', 'Vetch nitrogen credit to the following rice crop is not quantified.'],
      local_review: RICE_REVIEW, explainer_cards: ['cover_crop', 'nitrogen_fixing'],
      llm_report: { sentences: 9, numbers_checked: 23, rejected: 1, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'car2_dry_year_plan', loc: 'car_colusa_rice', name: 'Dry-year plan: fallow with cover or safflower', short: 'Dry-year plan', yearShown: 'dry year shown',
    tagline: 'When allocation drops under 50%: skip rice, plant safflower in April or hold a cover.',
    allocRule: { when: 'allocation_pct < 50', then: 'safflower or fallow with cover' },
    events: [{ year: 1, crop_id: 'safflower', plant: '04-01', harvest: '08-05', role: 'cash', timing_source: 'fao56_table11 (V: April planting, 20/35/45/25 days)' }],
    strip: 'pppcccpbbbbb', labels: L.car2, stripSource: 'fao56_table11',
    bare: [172, 140, 200], rain: [9, 5, 14], frost: [8, 4, 12], heat: [3, 1, 6], irr: [380, 290, 480], openet: null, openetPct: null,
    s: { water: [81, 72, 90], forage: [0, 0, 0], nfix: [12, 0, 25], erosion: [28, 15, 40], om: [30, 20, 41], market: [46, 30, 62], pest: [61, 48, 73], infil: [44, 32, 55], nscav: [25, 14, 36] },
    rma: [58, 20, 9, 13], rmaLabel: 'Colusa County · safflower / fallow',
    brief: {
      why: [
        sent('In a year like 2022, when allocations were cut and the block sat fallow, safflower planted in April uses a fraction of the water rice needs.', ['nasa_eo_rice_2022', 'fao56_table11'], ['2022']),
        sent('Irrigation need is about 380 mm (1.2 acre-ft/acre) against about 1,340 mm for rice.', ['fao56_table12'], ['380', '1.2', '1,340']),
      ],
      evidence: [sent('Safflower stage lengths of 20/35/45/25 days from an April planting in California.', ['fao56_table11'], ['20', '35', '45', '25'])],
      benefits: [], gaps: ['Safflower harvest month is assumed.', 'Local safflower market and contract availability unknown.'],
      local_review: RICE_REVIEW.slice(2), explainer_cards: ['drought_tolerant'],
      llm_report: { sentences: 3, numbers_checked: 9, rejected: 0, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'car3_rice_wheat', loc: 'car_colusa_rice', name: 'Rice–winter wheat', short: 'Rice–winter wheat', cycle: 2, yearShown: 'wheat year shown',
    tagline: 'Alternate rice with a winter wheat year drilled in Nov–Dec and cut in June.',
    events: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 2, crop_id: 'winter_wheat', plant: '11-20', harvest: '06-15', role: 'cash', timing_source: 'fao56_table11 (V: Calif. December); harvest assumed (U)' }],
    strip: 'pccccpbbbbpp', labels: L.car3, stripSource: 'fao56_table11',
    bare: [121, 95, 150], rain: [4, 2, 8], frost: [1, 0, 3], heat: [2, 0, 4], irr: [240, 150, 340], openet: null, openetPct: null,
    s: { water: [68, 58, 79], forage: [15, 5, 25], nfix: [0, 0, 0], erosion: [58, 45, 70], om: [52, 42, 62], market: [66, 50, 80], pest: [38, 26, 50], infil: [48, 36, 59], nscav: [55, 42, 67] },
    rma: [41, 34, 7, 18], rmaLabel: 'Colusa County · wheat',
    brief: {
      why: [
        sent('Winter wheat grows on winter rain and covers the field from December through May, the months your field is usually bare.', ['fao56_table11', 'hls'], []),
        sent('In the wheat year irrigation need is about 240 mm (0.8 acre-ft/acre).', ['fao56_table12'], ['240', '0.8']),
      ],
      evidence: [sent('Wheat is drilled November–December in California.', ['fao56_table11'], [])],
      benefits: [], gaps: ['Wheat harvest month is assumed.', 'Drainage of rice soil for a winter cereal needs a local check.'],
      local_review: RICE_REVIEW.slice(2), explainer_cards: ['deep_rooting'],
      llm_report: { sentences: 3, numbers_checked: 6, rejected: 0, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'caf0_alfalfa', loc: 'caf_tulare_forage', baseline: true, name: 'Alfalfa, 7–8 cuts, 4–5 year stand', short: 'Alfalfa (today)',
    tagline: 'What the field does today: alfalfa hay cut every 28 days from March to October.',
    events: [{ year: 1, crop_id: 'alfalfa_hay', plant: '09-25', harvest: 'cuts Mar–Oct', role: 'forage', timing_source: 'uc_alfalfa (V window)' }],
    strip: 'pcccccccccpp', labels: L.caf0, stripSource: 'uc_alfalfa',
    bare: [10, 0, 25], rain: [1, 0, 2], frost: [0, 0, 1], heat: [0, 0, 2], irr: [1320, 1180, 1460], openet: [1210, 1130, 1290], openetPct: -3,
    s: { water: [15, 8, 24], forage: [92, 84, 98], nfix: [85, 72, 94], erosion: [82, 72, 90], om: [74, 64, 83], market: [80, 66, 90], pest: [20, 10, 30], infil: [70, 58, 80], nscav: [30, 20, 41] },
    rma: [38, 27, 14, 21], rmaLabel: 'Tulare & Kings · alfalfa / forage',
    brief: {
      why: [sent('This is the baseline: alfalfa planted mid-September to October, cut on a 28-day schedule after the first cut.', ['uc_alfalfa'], ['28'], 'template')],
      evidence: [sent('OpenET measured about 1,210 mm for the season; modelled crop water use is within 3%.', ['openet'], ['1,210', '3'], 'template')],
      benefits: [], gaps: ['Number of cuts (7–8) is a typical value, not measured on this field.'], local_review: FORAGE_REVIEW.slice(0, 2), explainer_cards: ['nitrogen_fixing'],
      llm_report: { sentences: 2, numbers_checked: 4, rejected: 0, model: 'template only', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'caf1_grain_corn', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + silage corn', short: 'Small grain + corn',
    tagline: 'Classic dairy double crop: wheat/triticale silage off in April, corn silage by September.',
    events: [{ year: 1, crop_id: 'small_grain_silage', plant: '10-25', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'silage_corn', plant: '05-10', harvest: '08-30', role: 'forage', timing_source: 'assumed (U)' }],
    strip: 'cccppccpbppc', labels: L.caf1, stripSource: 'mock',
    bare: [45, 30, 65], rain: [3, 1, 6], frost: [1, 0, 3], heat: [4, 2, 8], irr: [940, 820, 1070], openet: [905, 840, 980], openetPct: 5,
    s: { water: [38, 28, 48], forage: [88, 78, 96], nfix: [0, 0, 0], erosion: [60, 48, 71], om: [50, 40, 60], market: [76, 62, 88], pest: [18, 9, 28], infil: [40, 29, 51], nscav: [72, 60, 83] },
    rma: [33, 22, 24, 21], rmaLabel: 'Tulare & Kings · corn silage',
    brief: {
      why: [
        sent('Winter small grain grows on cool-season rain, so most pumping is concentrated in the corn months of May to August.', ['fao56_table12'], []),
        sent('Irrigation need is about 940 mm (3.1 acre-ft/acre) against 1,320 mm for alfalfa.', ['fao56_table12'], ['940', '3.1', '1,320']),
      ],
      evidence: [sent('OpenET measured about 905 mm on nearby double-cropped fields; the model is within 5%.', ['openet'], ['905', '5'])],
      benefits: [], gaps: ['Silage corn and small-grain timing are typical San Joaquin Valley values, not cited.', 'Silage-corn end-stage Kc is unverified.'],
      local_review: FORAGE_REVIEW, explainer_cards: ['cover_crop'],
      llm_report: { sentences: 3, numbers_checked: 7, rejected: 0, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'caf2_grain_sorghum', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + sorghum-sudan', short: 'Small grain + sorghum-sudan',
    tagline: 'Same winter silage, but a summer forage that needs less water than corn.',
    events: [{ year: 1, crop_id: 'small_grain_silage', plant: '10-25', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'sorghum_sudan', plant: '05-10', harvest: 'cuts Jun–Aug', role: 'forage', timing_source: 'assumed (U)' }],
    strip: 'cccppcccpppc', labels: L.caf2, stripSource: 'mock',
    bare: [40, 25, 60], rain: [3, 1, 6], frost: [1, 0, 3], heat: [2, 1, 5], irr: [720, 610, 840], openet: null, openetPct: null,
    s: { water: [56, 45, 66], forage: [74, 62, 85], nfix: [0, 0, 0], erosion: [62, 50, 73], om: [54, 43, 64], market: [66, 50, 80], pest: [22, 12, 33], infil: [46, 35, 57], nscav: [74, 62, 85] },
    rma: [36, 21, 20, 23], rmaLabel: 'Tulare & Kings · forage sorghum',
    brief: {
      why: [
        sent('Sorghum-sudan gives three summer cuts with less water than corn, which matters under a pumping allocation.', ['fao56_table12'], ['three']),
        sent('Irrigation need is about 720 mm (2.4 acre-ft/acre), just inside a 2.5 acre-ft/acre allocation; the high end of the range is over it.', ['fao56_table12'], ['720', '2.4', '2.5']),
        sent('The Tulare Lake Subbasin was placed on probation on 16 April 2024, so pumping limits may tighten.', ['swrcb_probation_2024'], ['16 April 2024']),
      ],
      evidence: [
        sent('Cover calendar 2016–2025: the field read as water for several weeks in spring 2023 when Tulare Lake re-flooded.', ['hls', 'nbc_tulare_2023'], ['2023']),
        sent('Sorghum-sudan water savings versus corn are a widely stated extension position that still needs a UC or NRCS citation.', ['uc_alfalfa'], [], 'template'),
      ],
      benefits: [], gaps: ['Sorghum-sudan water saving versus corn is not yet cited.', 'All yields are unverified ranges.', 'Number of sorghum-sudan cuts is assumed.'],
      local_review: FORAGE_REVIEW, explainer_cards: ['drought_tolerant'],
      llm_report: { sentences: 6, numbers_checked: 14, rejected: 1, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
  strategy({
    id: 'caf3_short_alfalfa_break', loc: 'caf_tulare_forage', name: 'Shorter alfalfa stand + winter-cereal break', short: 'Alfalfa 3 yr + cereal break', cycle: 4, yearShown: 'break year shown',
    tagline: 'Three-year stand, then a winter cereal and a summer with no pumping before re-seeding.',
    events: [{ year: 4, crop_id: 'small_grain_silage', plant: '11-01', harvest: '04-20', role: 'forage', timing_source: 'assumed (U)' }, { year: 4, crop_id: 'alfalfa_hay', plant: '09-25', harvest: null, role: 'forage', timing_source: 'uc_alfalfa (V window)' }],
    strip: 'cccpbbbbpppp', labels: L.caf3, stripSource: 'uc_alfalfa',
    bare: [130, 105, 160], rain: [5, 2, 9], frost: [1, 0, 3], heat: [9, 5, 14], irr: [310, 220, 410], openet: null, openetPct: null,
    s: { water: [84, 75, 92], forage: [48, 36, 60], nfix: [40, 28, 54], erosion: [44, 32, 57], om: [58, 47, 68], market: [58, 42, 72], pest: [52, 40, 64], infil: [58, 46, 69], nscav: [50, 38, 62] },
    rma: [38, 27, 14, 21], rmaLabel: 'Tulare & Kings · alfalfa / forage',
    brief: {
      why: [
        sent('A summer with no irrigated crop is the simplest way to stay under a pumping cap in the break year.', ['fao56_table12'], []),
        sent('In the break year irrigation need is about 310 mm (1.0 acre-ft/acre); alfalfa is re-seeded mid-September to October.', ['fao56_table12', 'uc_alfalfa'], ['310', '1.0']),
      ],
      evidence: [sent('Alfalfa planting window of mid-September to October in the central San Joaquin Valley.', ['uc_alfalfa'], [])],
      benefits: [], gaps: ['Bare summer raises heat and dust exposure; not scored.', 'All yields are unverified ranges.'],
      local_review: FORAGE_REVIEW, explainer_cards: ['deep_rooting'],
      llm_report: { sentences: 3, numbers_checked: 6, rejected: 0, model: 'cached LLM + template fallback', cached_at: ACCESSED },
    },
  }),
];

// ---------- field-year calendar (weekly, 2016–2025) ----------
function fieldYear(locId) {
  const r = rng(locId === 'car_colusa_rice' ? 5 : 77);
  const years = [];
  for (let y = 2016; y <= 2025; y++) {
    const w = new Array(52).fill('c');
    const set = (a, b, s) => { for (let i = Math.max(0, a); i <= Math.min(51, b); i++) w[i] = s; };
    let greenup = null, senescence = null, crop;
    const j = () => Math.round((r() - 0.5) * 2); // ±1 week jitter
    if (locId === 'car_colusa_rice') {
      crop = y === 2022 ? 'Fallow/Idle' : 'Rice';
      const late = y === 2023 ? 3 : 0; // late planting and harvest after the 2023 storms
      if (y === 2022) {
        set(0, 51, 'b'); set(8, 15, 'p'); set(47, 51, 'p'); // winter weeds only; no winter flood (drought)
      } else {
        const winterFlood = y !== 2021 && y !== 2016; // some winters not flooded
        const drain = 5 + j();
        set(0, drain, winterFlood || y === 2023 ? 'w' : 'b');
        if (y === 2023) set(0, 11, 'w');
        set(y === 2023 ? 12 : drain + 1, 15 + late, 'b');
        set(16 + late, 18 + late, 'w'); // flood, water-seed
        set(19 + late, 21 + late, 'p');
        greenup = 21 + late;
        set(22 + late, 37 + late, 'c');
        senescence = 38 + late;
        set(38 + late, 39 + late, 'p');
        set(40 + late, 43 + late, 'b');
        set(44 + late, 51, y === 2021 ? 'b' : 'w'); // autumn 2021: no re-flood, drought
      }
    } else {
      crop = { 2019: 'Corn', 2020: 'Winter wheat / corn' }[y] ?? 'Alfalfa';
      if (crop === 'Alfalfa') {
        set(0, 4 + j(), 'p'); set(47 + j(), 51, 'p');
        // each cut leaves a partial week
        for (let k = 0; k < 8; k++) { const wk = 11 + k * 4 + (k > 3 ? j() : 0); w[wk] = 'p'; }
        greenup = 5;
        if (y === 2021) { set(34, 37, 'b'); set(38, 41, 'p'); greenup = 42; } // re-seeded stand
        if (y === 2023) { set(10, 17, 'w'); set(18, 20, 'b'); set(21, 22, 'p'); greenup = 23; } // Tulare Lake flood extent weeks
      } else if (crop === 'Corn') {
        set(0, 13, 'b'); set(6, 11, 'p'); set(14, 17, 'b'); set(18, 20, 'p'); greenup = 20; set(21, 34, 'c'); senescence = 35; set(35, 36, 'p'); set(37, 43, 'b'); set(44, 51, 'p');
      } else {
        set(0, 3, 'p'); set(4, 15, 'c'); set(16, 18, 'b'); set(19, 20, 'p'); greenup = 20; set(21, 34, 'c'); senescence = 35; set(35, 36, 'p'); set(37, 39, 'b'); set(40, 42, 'p'); set(43, 51, 'c');
      }
    }
    const rule = w.slice();
    // cloud gaps (> 30 days without a clear scene) in winter -> unknown for the rule detector
    const gaps = 1 + Math.floor(r() * 2);
    for (let g = 0; g < gaps; g++) {
      const start = r() < 0.5 ? Math.floor(r() * 7) : 45 + Math.floor(r() * 5);
      const len = 1 + Math.floor(r() * 2);
      for (let i = start; i < Math.min(52, start + len); i++) if (rule[i] !== 'w' || r() < 0.4) rule[i] = 'u';
    }
    // ML detector: fills most gaps, shifts some transitions by a week
    const ml = w.slice();
    for (let i = 1; i < 51; i++) {
      if (w[i] !== w[i + 1] && r() < (locId === 'car_colusa_rice' ? 0.3 : 0.1)) ml[i] = w[i + 1];
      if (w[i] === 'p' && r() < 0.06) ml[i] = 'c';
    }
    for (let i = 0; i < 52; i++) if (rule[i] === 'u' && r() < 0.25) ml[i] = 'u';
    // risk ticks (regional grid: POWER / IMERG), per week
    const risks = [];
    const wet = y === 2023 ? 9 : y === 2017 || y === 2019 ? 5 : y === 2022 || y === 2021 ? 1 : 3;
    for (let k = 0; k < wet; k++) risks.push({ week: y === 2023 ? Math.floor(r() * 12) : (r() < 0.6 ? Math.floor(r() * 10) : 44 + Math.floor(r() * 8)), type: 'rain' });
    const frost = 1 + Math.floor(r() * 3);
    for (let k = 0; k < frost; k++) risks.push({ week: r() < 0.5 ? Math.floor(r() * 6) : 47 + Math.floor(r() * 5), type: 'frost' });
    const heat = (y === 2021 || y === 2022 || y === 2024 ? 4 : 2) + Math.floor(r() * 2);
    for (let k = 0; k < heat; k++) risks.push({ week: 24 + Math.floor(r() * 12), type: 'heat' });
    years.push({ year: y, cdl_crop: crop, weeks: { rule: rule.join(''), ml: ml.join('') }, greenup_week: greenup, senescence_week: senescence, risks });
  }
  let agree = 0, total = 0;
  years.forEach((yr) => { for (let i = 0; i < 52; i++) { total++; if (yr.weeks.rule[i] === yr.weeks.ml[i]) agree++; } });
  return {
    location_id: locId, years,
    detector_agreement_pct: Math.round((100 * agree) / total),
    thresholds: { bare_ndvi_lt: 0.2, partial_ndvi: [0.2, 0.35], covered_ndvi_gt: 0.35, source: src('ndvi_usgs') },
    models: [
      { id: 'rule_ndvi', task: 'bare_cover', method: 'rule_ndvi', labels: 'none (thresholds)', metrics: { accuracy: 0.88, f1_bare: 0.84, transition_mae_days: 11 }, notes: 'NDVI thresholds; gaps over 30 days stay unknown.' },
      { id: 'bare_rf_v1', task: 'bare_cover', method: 'random_forest', labels: 'cdl_year_class + season_rules', split: { train_years: [2016, 2017, 2018, 2019, 2020, 2021, 2023], test_years: [2022, 2024, 2025] }, metrics: { accuracy: 0.92, f1_bare: 0.89, transition_mae_days: 8 }, notes: '2022 (fallow) held out as the test year; spatial hold-out by field.' },
    ],
  };
}

// ---------- news ----------
const news = {
  car_colusa_rice: [
    { date: '2022-05-01', title: 'A Rough Year for Rice in California', source: 'NASA Earth Observatory', url: SOURCES.nasa_eo_rice_2022.url, rank: 1, place_match: ['Sacramento Valley'], query_id: 'car_2022_drought', kind: 'drought', label: '2022 fallow', signal: { dataset: 'smap_l3', text: 'SMAP soil moisture in the driest 9% for the date', value_pct: 9, lead_days: null }, verified: true },
    { date: '2022-05-20', title: 'Calif. rice acreage to drop to 39-year low', source: 'Farm Progress', url: SOURCES.farmprogress_2022.url, rank: 2, place_match: ['Sacramento Valley'], query_id: 'car_2022_drought', kind: 'drought', label: '2022 fallow', signal: { dataset: 'smap_l3', text: 'SMAP soil moisture in the driest 9% for the date', value_pct: 9, lead_days: null }, verified: true },
    { date: '2023-01-09', title: 'Atmospheric rivers hit the Sacramento Valley, Jan–Mar 2023', source: 'headline to confirm', url: null, rank: 3, place_match: ['Sacramento Valley'], query_id: 'car_2023_storms', kind: 'flood', label: '2023 storms', signal: { dataset: 'imerg', text: 'IMERG 3-day rain above the 95th percentile', value_pct: 96, lead_days: null }, verified: false },
    { date: '2024-01-03', title: 'Later rice harvest deals minor yield, quality impacts', source: 'Ag Alert', url: SOURCES.agalert_2024.url, rank: 2, place_match: ['Sacramento Valley'], query_id: 'car_2023_storms', kind: 'flood', label: 'late 2023 harvest', signal: null, verified: true },
  ],
  caf_tulare_forage: [
    { date: '2022-07-01', title: '2021–22 drought and heavy groundwater pumping', source: 'headline to confirm', url: null, rank: 3, place_match: ['Kings County'], query_id: 'caf_2022_drought', kind: 'drought', label: '2022 drought', signal: { dataset: 'grace', text: 'GRACE groundwater storage in the lowest 5% since 2003', value_pct: 5, lead_days: null }, verified: false },
    { date: '2023-03-15', title: 'Dormant California lake reappeared and isn\'t going anywhere fast', source: 'NBC News', url: SOURCES.nbc_tulare_2023.url, rank: 3, place_match: ['Tulare Lake'], query_id: 'caf_2023_flood', kind: 'flood', label: '2023 Tulare Lake flood', signal: { dataset: 'imerg', text: 'IMERG 3-day rain above the 95th percentile', value_pct: 97, lead_days: null }, verified: true },
    { date: '2024-04-16', title: 'State Water Board places Tulare Lake Subbasin on probation', source: 'State Water Resources Control Board', url: SOURCES.swrcb_probation_2024.url, rank: 1, place_match: ['Tulare Lake Subbasin'], query_id: 'caf_2024_sgma', kind: 'policy', label: '2024 SGMA probation', signal: null, verified: true },
  ],
};

// ---------- write ----------
const w = (name, data) => writeFileSync(join(out, name), JSON.stringify(data));
w('locations.json', { locations, bc });
w('strategies.json', strategies);
w('cells.json', {
  car_colusa_rice: { scene_date: '2025-07-18', scene_source: src('hls'), et_source: src('openet'), type: 'FeatureCollection', features: carCells },
  caf_tulare_forage: { scene_date: '2025-07-21', scene_source: src('hls'), et_source: src('openet'), type: 'FeatureCollection', features: cafCells },
});
w('field-year.json', { car_colusa_rice: fieldYear('car_colusa_rice'), caf_tulare_forage: fieldYear('caf_tulare_forage') });
w('news.json', news);
w('sources.json', SOURCES);
console.log('mock written:', carCells.length, 'CAR cells,', cafCells.length, 'CAF cells; AF_MM', AF_MM);
