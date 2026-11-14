// Generates the illustrative mock data in src/mock/*.json.
// Shapes follow planner-spec.md B3 (Location, RotationStrategy, ModelReport, NewsItem, SourcedNumber).
// Numbers are ILLUSTRATIVE (method "assumed" / verified false) unless they are cited facts from the spec.
// Run: npm run mock
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'mock');
mkdirSync(OUT, { recursive: true });
const write = (name, data) => writeFileSync(join(OUT, name), JSON.stringify(data, null, 1));

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const r3 = (v) => Math.round(v * 1000) / 1000;
const r6 = (v) => Math.round(v * 1e6) / 1e6;

// ---------------------------------------------------------------- sources
const SOURCES = {
  mock: { id: 'mock', title: 'Illustrative mock value (frontend prototype)', url: null, verified: false },
  fao56_table12: { id: 'fao56_table12', title: 'FAO-56 Table 12, crop coefficients', url: 'https://www.fao.org/4/x0490e/x0490e0b.htm', verified: true },
  ssurgo_sda: { id: 'ssurgo_sda', title: 'USDA SSURGO via Soil Data Access', url: 'https://sdmdataaccess.sc.egov.usda.gov/', verified: true },
  uc_rice_blog: { id: 'uc_rice_blog', title: 'UC Rice Blog (planting and harvest timing)', url: 'https://www.ucanr.edu/blog/uc-rice-blog', verified: true },
  uc_alfalfa: { id: 'uc_alfalfa', title: 'UC Alfalfa: Irrigated Alfalfa Management', url: 'https://alfalfa.ucdavis.edu/IrrigatedAlfalfa', verified: true },
  cimis: { id: 'cimis', title: 'CIMIS station list', url: 'https://cimis.water.ca.gov/Stations.aspx', verified: true },
  openet: { id: 'openet', title: 'OpenET 30 m monthly ET (ensemble)', url: 'https://openet-api.org/raster/timeseries/point', verified: false },
  nasa_eo_rice: { id: 'nasa_eo_rice', title: 'NASA Earth Observatory: A Rough Year for Rice in California', url: 'https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/', verified: true },
  farmprogress_rice: { id: 'farmprogress_rice', title: 'Farm Progress: Calif. rice acreage to drop to 39-year low', url: 'https://www.farmprogress.com/rice/calif-rice-acreage-to-drop-to-39-year-low', verified: true },
  eqip_340: { id: 'eqip_340', title: 'USDA NRCS EQIP (practice 340 Cover Crop)', url: 'https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program', verified: false },
  power: { id: 'power', title: 'NASA POWER daily meteorology', url: 'https://power.larc.nasa.gov/', verified: false },
  hls: { id: 'hls', title: 'NASA Harmonized Landsat Sentinel-2 (HLS) 30 m', url: 'https://www.earthdata.nasa.gov/data/projects/hls', verified: false },
  smap: { id: 'smap', title: 'NASA SMAP soil moisture, 9 km EASE-2 grid', url: 'https://smap.jpl.nasa.gov/', verified: false },
  imerg: { id: 'imerg', title: 'NASA GPM IMERG daily precipitation', url: 'https://gpm.nasa.gov/data/imerg', verified: false },
  grace: { id: 'grace', title: 'GRACE / GRACE-FO data-assimilation drought indicators', url: 'https://nasagrace.unl.edu/', verified: false },
  cdl: { id: 'cdl', title: 'USDA NASS Cropland Data Layer 2008-2024', url: 'https://nassgeodata.gmu.edu/CropScape/', verified: false },
  rma: { id: 'rma', title: 'USDA RMA cause of loss 2010-2024', url: 'https://www.rma.usda.gov/tools-reports/summary-of-business/cause-loss', verified: false },
  bc_order: { id: 'bc_order', title: 'BC Gov News: fish population protection order, Salmon River and Bessette Creek (16 Aug 2023)', url: 'https://news.gov.bc.ca/releases/2023FOR0052-001305', verified: true },
};
const sn = (value, unit, low, high, method = 'assumed', source = 'mock', note = '') => ({
  value, unit, low, high, method, source: SOURCES[source], note,
});

// ---------------------------------------------------------------- geometry
const M_PER_DEG = 111320;
function toLonLat(c, xm, ym) {
  return [r6(c.lon + xm / (M_PER_DEG * Math.cos((c.lat * Math.PI) / 180))), r6(c.lat + ym / M_PER_DEG)];
}
function poly(c, pts) {
  const ring = pts.map(([x, y]) => toLonLat(c, x, y));
  ring.push(ring[0]);
  return { type: 'Polygon', coordinates: [ring] };
}
function inside(pts, x, y) {
  let ins = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
const square = (c, x0, y0, size) => poly(c, [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size]]);

const PRESETS = {
  car_colusa_rice: {
    c: { lon: -122.1, lat: 39.15 },
    // 1000 m x 600 m laser-levelled check with the NE corner cut by a supply canal (~59 ha)
    pts: [[-500, -300], [500, -300], [500, 150], [350, 300], [-500, 300]],
    area: 58.9,
    smapOrigin: [-820, -760], // SW corner of the 9 km cell relative to the field centre, metres
    modisOrigin: [-790, -290],
  },
  caf_tulare_forage: {
    c: { lon: -119.6, lat: 36.2 },
    // 400 m x 800 m furrow-irrigated block (32 ha)
    pts: [[-200, -400], [200, -400], [200, 400], [-200, 400]],
    area: 32.0,
    smapOrigin: [-560, -900],
    modisOrigin: [-490, -390],
  },
};

// ---------------------------------------------------------------- 30 m cells (zones)
function cells(id) {
  const p = PRESETS[id];
  const rand = rng(id === 'car_colusa_rice' ? 11 : 29);
  const xs = p.pts.map((q) => q[0]), ys = p.pts.map((q) => q[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const feats = [];
  const S = 30, G = 1.6; // cell size and visual gap (m)
  const rice = id === 'car_colusa_rice';
  // hotspot: rice = cold-water inlet corner (NW); forage = sandy streak mid-field
  const hot = rice ? { x: -380, y: 210, r: 150 } : { x: 60, y: 120, r: 130 };
  const hot2 = rice ? { x: 250, y: -170, r: 90 } : { x: -110, y: -260, r: 80 };
  let n = 0;
  for (let j = 0, y = y0; y < y1 - 1; y += S, j++) {
    for (let i = 0, x = x0; x < x1 - 1; x += S, i++) {
      const cx = x + S / 2, cy = y + S / 2;
      if (!inside(p.pts, cx, cy)) continue;
      const smooth = 0.5 * Math.sin(cx / 170 + 1.3) * Math.cos(cy / 140 - 0.4) + 0.3 * Math.sin((cx + cy) / 95);
      const h1 = Math.exp(-((cx - hot.x) ** 2 + (cy - hot.y) ** 2) / (2 * hot.r ** 2));
      const h2 = Math.exp(-((cx - hot2.x) ** 2 + (cy - hot2.y) ** 2) / (2 * hot2.r ** 2));
      const noise = rand() - 0.5;
      // rice: check levees every 210 m read slightly lower; forage: borders every 120 m
      const levee = rice ? (Math.abs(((cx + 500) % 210) - 105) > 92 ? 1 : 0) : (Math.abs(((cy + 400) % 160) - 80) > 68 ? 1 : 0);
      const edge = Math.min(cx - x0, x1 - cx, cy - y0, y1 - cy) < 30 ? 1 : 0;
      const stressRaw = clamp(0.95 * h1 + 0.7 * h2 + 0.08 * noise + 0.05 * levee, 0, 1);
      const base = rice ? 0.8 : 0.74;
      const ndvi = clamp(base + 0.06 * smooth - 0.3 * h1 - 0.2 * h2 - 0.07 * levee - 0.05 * edge + 0.05 * noise, 0.2, 0.93);
      const etBase = rice ? 1045 : 1180;
      const et = Math.round(etBase * (0.62 + 0.46 * (ndvi / base)) + 28 * noise);
      const bare = Math.round(clamp((rice ? 62 : 8) + 70 * h1 + 40 * h2 + 14 * levee + 10 * edge + 10 * noise - 8 * smooth, 0, 200));
      feats.push({
        type: 'Feature',
        id: n++,
        properties: {
          i, j,
          ndvi: r3(ndvi), // peak-season (Jul-Aug) median NDVI, HLS 30 m
          et_mm: et, // growing-season ET, OpenET ensemble
          stress: r3(stressRaw), // hotspot score 0-1 (NDVI anomaly / ECOSTRESS LST)
          hotspot: stressRaw > 0.45,
          bare_days: bare, // mean bare days per year 2016-2025
          v: r3(clamp(0.5 + 0.9 * smooth - 0.9 * h1 - 0.6 * h2 + 0.5 * noise, -1, 1)), // within-field variation for replay
        },
        geometry: poly(p.c, [[x + G, y + G], [x + S - G, y + G], [x + S - G, y + S - G], [x + G, y + S - G]]),
      });
    }
  }
  return {
    location_id: id,
    grid: 'HLS 30 m (UTM 10N)',
    cell_size_m: 30,
    measures: {
      ndvi: { label: 'Cover (NDVI)', unit: 'NDVI', dataset: 'hls', source: SOURCES.hls },
      et_mm: { label: 'Water use (ET)', unit: 'mm/season', dataset: 'openet', source: SOURCES.openet },
      stress: { label: 'Stress hotspot', unit: 'score 0-1', dataset: 'hls + ecostress', source: SOURCES.hls },
      bare_days: { label: 'Bare days', unit: 'days/yr', dataset: 'hls', source: SOURCES.hls },
    },
    hotspot_note: rice
      ? 'Hotspot in the north-west corner sits by the water inlet: cold-water effect is a known cause, confirm on the ground.'
      : 'Hotspot streak mid-field: could be a sandy lens or an irrigation set that runs short. Confirm on the ground.',
    slope_note: rice ? 'Levelled field, slope zones not meaningful.' : 'Near-flat field (slope under 0.5%), slope zones not meaningful.',
    footprints: {
      smap_9km: { label: 'SMAP soil-moisture pixel, 9 km', size_m: 9000, geometry: square(p.c, p.smapOrigin[0], p.smapOrigin[1], 9000) },
      modis_250m: { label: 'MODIS pixel, 250 m', size_m: 250, geometry: square(p.c, p.modisOrigin[0], p.modisOrigin[1], 250) },
      hls_30m: { label: 'HLS / OpenET cell, 30 m', size_m: 30 },
    },
    cells: { type: 'FeatureCollection', features: feats },
  };
}

// ---------------------------------------------------------------- field's year (weekly features)
// classes: b bare, p partial, c covered, w water, u unknown (cloud gap > 30 days)
function yearCAR(year, rand) {
  const w = new Array(52).fill('b');
  const set = (a, b, c) => { for (let i = Math.max(0, a); i <= Math.min(51, b); i++) w[i] = c; };
  const drought = year === 2021 || year === 2022;
  const late = year === 2023 ? 3 : year === 2019 ? 1 : 0;
  if (year === 2022) {
    // fallow: no winter flood, weedy spring flush, bare summer, storms arrive late Dec
    set(0, 9, 'b'); set(10, 18, 'p'); set(19, 49, 'b'); set(50, 51, 'w');
    return w;
  }
  set(0, year === 2023 ? 11 : 7, 'w'); // winter flood (2023: storms keep water on to late March)
  set(year === 2023 ? 12 : 8, 16 + late, 'b');
  set(17 + late, 19 + late, 'w'); // flood, water-seed
  set(20 + late, 21 + late, 'p');
  set(22 + late, 38 + late, 'c');
  set(39 + late, 41 + late, 'p'); // drain, harvest
  set(42 + late, 43 + late, 'b'); // straw management
  if (drought) set(44, 51, 'b'); else set(44 + late, 51, 'w');
  for (const i of [0, 1, 2, 3, 4, 5, 46, 47, 48, 49, 50, 51]) if (rand() < 0.1 && year !== 2023) w[i] = 'u';
  return w;
}
function yearCAF(year, rand) {
  const w = new Array(52).fill('c');
  const set = (a, b, c) => { for (let i = a; i <= b; i++) w[i] = c; };
  if (year === 2020) {
    // winter wheat silage then silage corn, alfalfa re-seeded in October
    set(0, 15, 'c'); set(16, 17, 'b'); set(18, 20, 'p'); set(21, 34, 'c'); set(35, 39, 'b'); set(40, 51, 'p');
    return w;
  }
  set(0, 5, 'p'); set(48, 51, 'p');
  for (let i = 10 + (year % 3); i < 44; i += 4) w[i] = 'p'; // week after each cutting
  if (year === 2023) set(12, 14, 'w');
  if (year === 2021) set(0, 8, 'p'); // establishment year after 2020 re-seed
  for (const i of [0, 1, 2, 3, 49, 50, 51]) if (rand() < 0.1) w[i] = 'u';
  return w;
}
function mlFrom(rule, year, id, rand) {
  const ml = rule.slice();
  for (let i = 1; i < 51; i++) {
    if (rule[i] === 'u') continue;
    const edge = rule[i] !== rule[i - 1] || rule[i] !== rule[i + 1];
    if (edge && rand() < (id === 'car_colusa_rice' ? 0.27 : 0.11)) {
      const nb = rule[i] !== rule[i - 1] ? rule[i - 1] : rule[i + 1];
      if (nb !== 'u') ml[i] = nb;
    }
  }
  if (id === 'car_colusa_rice' && year === 2022) for (let i = 13; i <= 18; i++) ml[i] = 'b'; // ML reads weedy fallow as bare
  return ml;
}
function ndviSeries(classes, rand) {
  const target = { b: 0.14, p: 0.3, c: 0.78, w: 0.04, u: NaN };
  let raw = classes.map((c) => target[c]);
  for (let i = 0; i < 52; i++) if (Number.isNaN(raw[i])) raw[i] = raw[i - 1] ?? raw.find((v) => !Number.isNaN(v));
  return raw.map((_, i) => {
    const a = raw[Math.max(0, i - 1)], b = raw[i], c = raw[Math.min(51, i + 1)];
    return r3(clamp((a + 2 * b + c) / 4 + (rand() - 0.5) * 0.04, 0.02, 0.92));
  });
}
function risks(year, id, rand) {
  const wet = { 2017: 0.5, 2019: 0.35, 2023: 0.6, 2024: 0.25 }[year] ?? 0.1;
  const hotY = { 2017: 0.35, 2020: 0.4, 2021: 0.55, 2022: 0.6, 2024: 0.55 }[year] ?? 0.25;
  const rain = [], frost = [], heat = [], rainMm = [];
  for (let i = 0; i < 52; i++) {
    const winter = i < 12 || i > 44;
    let mm = winter ? Math.round(rand() * rand() * (60 + 260 * wet)) : i < 18 || i > 40 ? Math.round(rand() * rand() * 30) : 0;
    if (year === 2023 && (i <= 2 || (i >= 8 && i <= 11))) mm = 70 + Math.round(rand() * 60);
    if (year === 2022 && i > 2 && i < 48) mm = Math.round(mm * 0.3);
    if (year === 2022 && i >= 50) mm = 60 + Math.round(rand() * 40);
    if (id === 'caf_tulare_forage') mm = Math.round(mm * 0.45);
    rainMm.push(mm);
    if (mm >= (id === 'caf_tulare_forage' ? 30 : 55)) rain.push(i);
    if ((i < 6 || i > 47) && rand() < 0.22) frost.push(i);
    if (i >= 25 && i <= 36 && rand() < hotY) heat.push(i);
  }
  return { rain, frost, heat, rainMm };
}
function yearData(id) {
  const rand = rng(id === 'car_colusa_rice' ? 101 : 202);
  const rice = id === 'car_colusa_rice';
  const cdl = rice
    ? { 2016: 'Rice', 2017: 'Rice', 2018: 'Rice', 2019: 'Rice', 2020: 'Rice', 2021: 'Rice', 2022: 'Fallow/Idle', 2023: 'Rice', 2024: 'Rice', 2025: null }
    : { 2016: 'Alfalfa', 2017: 'Alfalfa', 2018: 'Alfalfa', 2019: 'Alfalfa', 2020: 'Winter wheat / Corn', 2021: 'Alfalfa', 2022: 'Alfalfa', 2023: 'Alfalfa', 2024: 'Alfalfa', 2025: null };
  const years = [];
  let same = 0, total = 0;
  for (let y = 2016; y <= 2025; y++) {
    const rule = rice ? yearCAR(y, rand) : yearCAF(y, rand);
    const ml = mlFrom(rule, y, id, rand);
    rule.forEach((c, i) => { if (c !== 'u') { total++; if (c === ml[i]) same++; } });
    const rk = risks(y, id, rand);
    const stress = [];
    for (let i = 22; i <= 38; i++) {
      const hot = rk.heat.includes(i);
      if (hot && rand() < 0.5) stress.push({ week: i, flagged_by: rand() < 0.5 ? 'both' : 'one' });
    }
    years.push({
      year: y,
      cdl_class: cdl[y],
      rule: rule.join(''),
      ml: ml.join(''),
      ndvi: ndviSeries(rule, rand),
      rain_mm: rk.rainMm,
      risk_weeks: { extreme_rain: rk.rain, frost: rk.frost, heat: rk.heat },
      stress_weeks: stress,
      bare_days: rule.filter((c) => c === 'b').length * 7,
    });
  }
  return {
    location_id: id,
    cadence: 'weekly',
    classes: { b: 'bare', p: 'partial', c: 'covered', w: 'water', u: 'unknown' },
    thresholds: { bare_ndvi_below: 0.2, covered_ndvi_above: 0.35, water: 'NDWI > 0.3 or SCL 6 / DSWx', unknown: 'no clear view within 30 days', verified: false },
    risk_rules: { extreme_rain: 'P >= 25 mm/day or 3-day >= 75 mm (our definition)', frost: 'Tmin <= 0 C', heat: 'Tmax >= 35 C' },
    detector_agreement_pct: sn(Math.round((100 * same) / total), '%', null, null, 'model', 'mock', 'rule vs ML, weeks with a clear view'),
    years,
  };
}

// ---------------------------------------------------------------- regional trends (11 x 11 cells)
function trends(id) {
  const p = PRESETS[id];
  const rand = rng(id === 'car_colusa_rice' ? 301 : 302);
  const n = 11, size = 9000;
  const ox = p.smapOrigin[0] - 5 * size, oy = p.smapOrigin[1] - 5 * size;
  const feats = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const g1 = Math.sin(i / 2.6 + (id.length % 3)) * Math.cos(j / 3.1);
    const g2 = Math.sin((i + j) / 5.2 + 0.8);
    feats.push({
      type: 'Feature',
      properties: {
        row: j, col: i, home: i === 5 && j === 5,
        smap_anomaly: r3(clamp(-0.045 + 0.022 * g1 + 0.012 * (rand() - 0.5), -0.09, 0.03)), // m3/m3, growing season 2022 vs 2015-2025
        grace_gw_pct: Math.round(clamp((id === 'car_colusa_rice' ? 14 : 5) + 6 * g2 + 2 * (rand() - 0.5), 1, 40)), // percentile, 2022
      },
      geometry: square(p.c, ox + i * size, oy + j * size, size),
    });
  }
  const series = (from, to, f) => Array.from({ length: to - from + 1 }, (_, k) => ({ year: from + k, value: f(from + k) }));
  const dry = { 2007: -8, 2008: -12, 2009: -10, 2013: -14, 2014: -24, 2015: -30, 2016: -18, 2020: -14, 2021: -28, 2022: -34, 2024: -6 };
  const base = id === 'car_colusa_rice' ? 52 : 38;
  const slope = id === 'car_colusa_rice' ? -0.5 : -1.1;
  return {
    location_id: id,
    grid: { name: 'EASE2_G9km', n, cell_m: size },
    layers: {
      smap_anomaly: { label: 'Soil moisture anomaly, growing season 2022', unit: 'm3/m3', year: 2022, dataset: 'smap_l3', source: SOURCES.smap, domain: [-0.09, 0.03] },
      grace_gw_pct: { label: 'Groundwater storage percentile, 2022', unit: 'percentile', year: 2022, dataset: 'grace', source: SOURCES.grace, domain: [0, 40], note: 'GRACE senses ~300 km; cells are a model downscaling, not field values.' },
    },
    cells: { type: 'FeatureCollection', features: feats },
    series: {
      grace_gw_pct: series(2003, 2025, (y) => Math.round(clamp(base + slope * (y - 2003) + (dry[y] ?? 6) + 6 * (rand() - 0.5), 2, 90))),
      smap_anomaly: series(2015, 2025, (y) => r3(((dry[y] ?? 8) / 1000) + 0.01 * (rand() - 0.5))),
      heatwave_days: series(2003, 2025, (y) => Math.round((id === 'car_colusa_rice' ? 22 : 41) + 0.45 * (y - 2003) + 8 * (rand() - 0.5) + (dry[y] ? 5 : 0))),
    },
    event_markers: id === 'car_colusa_rice'
      ? [{ year: 2022, label: '2022 fallow' }, { year: 2023, label: '2023 storms' }]
      : [{ year: 2023, label: '2023 Tulare Lake' }, { year: 2024, label: '2024 probation' }],
  };
}

// ---------------------------------------------------------------- locations
const locations = [
  {
    id: 'car_colusa_rice', name: 'Colusa County rice check (example)', short_name: 'Colusa rice', place_line: 'West of Williams, Sacramento Valley, CA',
    region_adapter: 'ca', regime: 'drought_then_flood', state_fips: '06', county_fips: '011', ground_data: 'rich',
    geometry: poly(PRESETS.car_colusa_rice.c, PRESETS.car_colusa_rice.pts), centroid: PRESETS.car_colusa_rice.c,
    area_ha: sn(58.9, 'ha', null, null, 'computed', 'mock', 'Example field; drag to your own'), crs_working: 'EPSG:32610',
    soil: { mukey: null, muname: 'Willows silty clay (illustrative)', drainage_class: 'Poorly drained', hydrologic_group: 'D', awc_mm_per_m: sn(150, 'mm/m', 130, 170), om_pct: sn(2.4, '%', 1.8, 3.0), texture_class: 'Silty clay', source: SOURCES.ssurgo_sda },
    terrain: { slope_mean_pct: sn(0.05, '%', 0, 0.1), slope_p90_pct: sn(0.1, '%', 0, 0.2), elev_m: sn(22, 'm', 21, 23), low_spot_fraction: sn(0, 'fraction', 0, 0.02), note: 'Laser-levelled: slope zones not meaningful.' },
    water: { source: 'surface', allocation_input: { unit: 'acre-ft/acre', value: 3.8 }, district: 'Glenn-Colusa ID (unverified)', sgma_subbasin: 'Colusa', sgma_status: { text: 'Colusa Subbasin: medium priority (unverified)', url: 'https://sgma.water.ca.gov/', verified: false }, cdec_stations: ['SHA', 'ORO'] },
    market_preference: 'sell',
    stations: [{ network: 'CIMIS', id: 250, name: 'Williams', distance_km: 8, years: [2016, 2026], url: SOURCES.cimis.url }, { network: 'NOAA', id: null, name: 'Colusa / Williams daily (station id to confirm)' }, { network: 'CDEC', id: 'SHA', name: 'Shasta storage' }, { network: 'CDEC', id: 'ORO', name: 'Oroville storage' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0, footprint: square(PRESETS.car_colusa_rice.c, ...PRESETS.car_colusa_rice.smapOrigin, 9000) },
    datasets: ['power', 'imerg', 'smap_l3', 'smap_l4', 'hls', 's2', 'modis', 'ecostress', 'grace', 'dem', 'cdl', 'openet', 'cimis', 'cdec', 'dwr_wells', 'rma', 'usdm', 'news'],
    crop_history: { 2008: 'Rice', 2009: 'Rice', 2010: 'Rice', 2011: 'Rice', 2012: 'Rice', 2013: 'Rice', 2014: 'Rice', 2015: 'Rice', 2016: 'Rice', 2017: 'Rice', 2018: 'Rice', 2019: 'Rice', 2020: 'Rice', 2021: 'Rice', 2022: 'Fallow/Idle', 2023: 'Rice', 2024: 'Rice' },
    observed_cover: { typically_bare_doy_ranges: [[290, 110]], years_used: [2016, 2025], detector: 'consensus', summary: 'Bare mid-Oct to late Apr, except winter-flood years' },
    baseline_summary: 'Continuous rice with winter flooding',
    events: [
      { date: '2022-05-01', type: 'drought_fallow', title: 'Sacramento Valley rice acreage roughly halved', url: SOURCES.nasa_eo_rice.url, verified: true },
      { date: '2023-01-09', type: 'atmospheric_river', title: 'Jan-Mar 2023 atmospheric rivers; late planting and harvest', url: null, verified: false },
    ],
  },
  {
    id: 'caf_tulare_forage', name: 'Tulare/Kings forage block (example)', short_name: 'Tulare/Kings forage', place_line: 'Between Corcoran and Hanford, San Joaquin Valley, CA',
    region_adapter: 'ca', regime: 'groundwater_cap', state_fips: '06', county_fips: '031', ground_data: 'rich',
    geometry: poly(PRESETS.caf_tulare_forage.c, PRESETS.caf_tulare_forage.pts), centroid: PRESETS.caf_tulare_forage.c,
    area_ha: sn(32.0, 'ha', null, null, 'computed', 'mock', 'Example field; drag to your own'), crs_working: 'EPSG:32610',
    soil: { mukey: null, muname: 'Kimberlina fine sandy loam (illustrative)', drainage_class: 'Well drained', hydrologic_group: 'B', awc_mm_per_m: sn(130, 'mm/m', 110, 150), om_pct: sn(1.1, '%', 0.7, 1.5), texture_class: 'Fine sandy loam', source: SOURCES.ssurgo_sda },
    terrain: { slope_mean_pct: sn(0.2, '%', 0.1, 0.4), slope_p90_pct: sn(0.4, '%', 0.2, 0.6), elev_m: sn(64, 'm', 63, 66), low_spot_fraction: sn(0.03, 'fraction', 0, 0.06), note: 'Near-flat: slope zones not meaningful.' },
    water: { source: 'groundwater', allocation_input: { unit: 'acre-ft/acre', value: 2.5 }, district: 'GSA allocation (your number)', sgma_subbasin: 'Tulare Lake', sgma_status: { text: 'Tulare Lake Subbasin placed on probation 16 Apr 2024; status is in litigation and changes', url: 'https://www.waterboards.ca.gov/sgma/', verified: true }, cdec_stations: ['PNF'] },
    market_preference: 'feed_own_herd',
    stations: [{ network: 'CIMIS', id: 15, name: 'Stratford (to confirm)', distance_km: 21, years: [2016, 2026], url: SOURCES.cimis.url }, { network: 'NOAA', id: null, name: 'Hanford daily (station id to confirm)' }, { network: 'CDEC', id: 'PNF', name: 'Pine Flat storage' }, { network: 'DWR', id: null, name: 'Groundwater wells, depth to water' }],
    regional_cell: { grid: 'EASE2_G9km', row: 0, col: 0, footprint: square(PRESETS.caf_tulare_forage.c, ...PRESETS.caf_tulare_forage.smapOrigin, 9000) },
    datasets: ['power', 'imerg', 'smap_l3', 'smap_l4', 'hls', 's2', 'modis', 'ecostress', 'grace', 'dem', 'cdl', 'openet', 'cimis', 'cdec', 'dwr_wells', 'rma', 'usdm', 'news'],
    crop_history: { 2008: 'Cotton', 2009: 'Cotton', 2010: 'Winter wheat / Corn', 2011: 'Winter wheat / Corn', 2012: 'Alfalfa', 2013: 'Alfalfa', 2014: 'Alfalfa', 2015: 'Alfalfa', 2016: 'Alfalfa', 2017: 'Alfalfa', 2018: 'Alfalfa', 2019: 'Alfalfa', 2020: 'Winter wheat / Corn', 2021: 'Alfalfa', 2022: 'Alfalfa', 2023: 'Alfalfa', 2024: 'Alfalfa' },
    observed_cover: { typically_bare_doy_ranges: [], years_used: [2016, 2025], detector: 'consensus', summary: 'Covered most of the year; short partial-cover dips after each cutting' },
    baseline_summary: 'Alfalfa, 7-8 cuts, 4-5 year stand',
    events: [
      { date: '2023-03-20', type: 'flood', title: 'Tulare Lake re-floods (about 114,000 acres at peak)', url: null, verified: true },
      { date: '2024-04-16', type: 'sgma', title: 'Tulare Lake Subbasin placed on SGMA probation', url: 'https://www.waterboards.ca.gov/sgma/', verified: true },
    ],
  },
];

// ---------------------------------------------------------------- strategies
const SCORE_KEYS = ['water_use', 'forage_value', 'n_fixation', 'erosion', 'organic_matter', 'market', 'pest_break', 'infiltration', 'n_scavenging'];
const score = (v, lo, hi) => sn(v, 'score 0-100', lo, hi, 'model');
function strat(o) {
  const scores = {};
  SCORE_KEYS.forEach((k, i) => { scores[k] = score(...o.s[i]); });
  const six = SCORE_KEYS.slice(0, 6).map((k) => scores[k]);
  const avg = (f) => Math.round(six.reduce((a, s) => a + f(s), 0) / 6);
  return {
    id: o.id, location_id: o.loc, name: o.name, short: o.short, is_baseline: !!o.base, cycle_years: o.cycle ?? 1,
    one_line: o.line,
    calendar: o.calendar,
    month_labels: o.months, month_cover: o.cover, shown_year: o.shown ?? null,
    allocation_rule: o.rule ?? null,
    exposure: {
      cover_basis: o.base ? 'observed consensus cover (HLS / Sentinel-2)' : 'modelled cover',
      bare_days_per_year: sn(o.bare[0], 'days/yr', o.bare[1], o.bare[2], 'model'),
      exposed_rain_days: sn(o.rain[0], 'days/yr', o.rain[1], o.rain[2], 'model'),
      exposed_heat_days: sn(o.heat[0], 'days/yr', o.heat[1], o.heat[2], 'model'),
      exposed_frost_days: sn(o.frost[0], 'days/yr', o.frost[1], o.frost[2], 'model'),
      replay: {
        2022: { exposed_rain_days: sn(o.r22[0], 'days', null, null, 'model'), irrigation_need_mm: sn(o.r22[1], 'mm', null, null, 'model'), note: o.r22[2] },
        2023: { exposed_rain_days: sn(o.r23[0], 'days', null, null, 'model'), irrigation_need_mm: sn(o.r23[1], 'mm', null, null, 'model'), note: o.r23[2] },
      },
      scenario: { dT_c: 0, dP_pct: 0 },
    },
    water: {
      etc_mm_season: sn(o.etc[0], 'mm', o.etc[1], o.etc[2], 'model', 'fao56_table12'),
      irrigation_need_mm: sn(o.need[0], 'mm', o.need[1], o.need[2], 'model'),
      openet_et_mm_season: o.openet ? sn(o.openet, 'mm', null, null, 'measured', 'openet') : null,
      etc_vs_openet_pct: o.openet ? sn(Math.round((100 * (o.etc[0] - o.openet)) / o.openet), '%', null, null, 'computed', 'openet') : null,
    },
    scores,
    income: sn(o.income[0], 'USD/ha', o.income[1], o.income[2], 'assumed', 'mock', 'range, confirm locally'),
    composite: { value: avg((s) => s.value), low: avg((s) => s.low), high: avg((s) => s.high), weights_used: Object.fromEntries(SCORE_KEYS.slice(0, 6).map((k) => [k, 2])) },
    risk_profile: o.rma,
    funding: [{ program: 'USDA EQIP practice 340 Cover Crop', rate_per_acre_usd: { value: null, method: 'assumed' }, url: SOURCES.eqip_340.url, verified: false }],
    brief: {
      why: o.why.map((text) => ({ text, source_ids: ['mock'], author: 'template', checked: true })),
      local_review: o.review.map(([item, severity]) => ({ item, severity })),
      llm_report: { sentences: o.why.length, numbers_checked: 14, rejected: 0, model: 'template (mock)', cached_at: '2026-11-14' },
    },
    uncertainty: { agronomic_gap_count: o.gaps ?? 2, detector_disagreement_pct: 7 },
  };
}
const RMA_RICE = { rma_share_drought: sn(0.58, 'share', null, null, 'assumed'), rma_share_excess_moisture: sn(0.22, 'share', null, null, 'assumed'), rma_share_heat: sn(0.05, 'share', null, null, 'assumed'), rma_share_other: sn(0.15, 'share', null, null, 'assumed'), rma_years: [2010, 2024], crop: 'Rice, Colusa County' };
const RMA_FORAGE = { rma_share_drought: sn(0.41, 'share', null, null, 'assumed'), rma_share_excess_moisture: sn(0.18, 'share', null, null, 'assumed'), rma_share_heat: sn(0.21, 'share', null, null, 'assumed'), rma_share_other: sn(0.2, 'share', null, null, 'assumed'), rma_years: [2010, 2024], crop: 'Forage and corn, Tulare and Kings' };

const strategies = {
  car_colusa_rice: [
    strat({ id: 'car0_rice_winterflood', loc: 'car_colusa_rice', base: true, name: 'Continuous rice, winter flood', short: 'Current: rice + winter flood', line: 'What the field does now.',
      calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }],
      months: ['winter flood', 'drain', 'field prep', 'flood, water-seed', 'rice', 'rice', 'rice', 'rice', 'drain, harvest', 'straw, re-flood', 'winter flood', 'winter flood'], cover: 'wbbwccccpbww',
      bare: [62, 48, 75], rain: [3, 1, 5], heat: [0, 0, 1], frost: [1, 0, 3],
      r22: [0, 0, 'Fallowed: no allocation to plant'], r23: [2, 1180, 'Storms kept the field wet; planting 3 weeks late'],
      etc: [1010, 930, 1090], need: [1340, 1180, 1520], openet: 1045,
      s: [[22, 15, 30], [0, 0, 0], [0, 0, 0], [18, 12, 25], [48, 40, 56], [78, 60, 90], [0, 0, 0], [30, 22, 38], [12, 5, 20]],
      income: [0, 0, 0], rma: RMA_RICE,
      why: ['This is the baseline every alternative is compared against.'], review: [['Straw decomposition without burning', 'medium'], ['Waterfowl habitat obligations', 'medium']] }),
    strat({ id: 'car1_rice_wintercover', loc: 'car_colusa_rice', name: 'Rice + winter cover (no winter flood)', short: 'Rice + winter cover', line: 'Cereal/vetch cover replaces the winter flood.',
      calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 1, crop_id: 'cereal_vetch_cover', plant: '10-25', terminate: '03-20', role: 'cover', timing_source: 'assumed (U)' }],
      months: ['cover', 'cover', 'terminate, prep', 'flood, seed', 'rice', 'rice', 'rice', 'rice', 'harvest', 'drill cover', 'cover', 'cover'], cover: 'ccpwccccppcc',
      bare: [24, 14, 38], rain: [1, 0, 3], heat: [0, 0, 1], frost: [0, 0, 2],
      r22: [0, 0, 'No rice water; cover could still be drilled on rain'], r23: [1, 1020, 'Cover holds soil through Jan-Mar storms; termination may slip'],
      etc: [1090, 990, 1190], need: [1150, 1010, 1300], openet: 1045,
      s: [[34, 24, 43], [10, 0, 20], [28, 15, 40], [62, 48, 74], [66, 55, 76], [72, 55, 86], [22, 10, 33], [52, 40, 63], [70, 55, 82]],
      income: [85, 20, 150], rma: RMA_RICE, gaps: 3,
      why: ['Swaps about two months of winter flood water for a rain-fed cover crop.', 'Cuts bare days from 62 to 24 a year in the model.', 'Cover-crop species after rice are still under UC trial; treat the cover as a test strip first.'],
      review: [['Straw decomposition without winter flood', 'high'], ['Waterfowl habitat obligations', 'high'], ['Herbicide carryover to the cover crop', 'medium']] }),
    strat({ id: 'car2_dry_year_plan', loc: 'car_colusa_rice', name: 'Dry-year plan: cover or safflower', short: 'Dry-year plan', line: 'Used only when allocation is under 50%. Dry year shown.', shown: 'dry year',
      rule: 'if allocation < 50%: fallow with cover, or safflower',
      calendar: [{ year: 1, crop_id: 'safflower', plant: '04-01', harvest: '07-25', role: 'cash', timing_source: 'fao56_table11 California April (V)' }],
      months: ['cover / bare', 'cover / bare', 'plant safflower', 'safflower', 'safflower', 'safflower', 'harvest', 'bare', 'bare', 'bare', 'bare', 'bare'], cover: 'pppcccpbbbbb',
      bare: [158, 130, 190], rain: [6, 3, 9], heat: [24, 16, 32], frost: [2, 0, 4],
      r22: [1, 370, 'Would have kept a crop on the field in the fallow year'], r23: [8, 300, 'Wet spring delays April planting; bare autumn exposed'],
      etc: [520, 450, 600], need: [390, 300, 480],
      s: [[78, 68, 88], [0, 0, 0], [8, 0, 18], [30, 15, 46], [34, 24, 45], [44, 25, 62], [55, 40, 67], [48, 36, 60], [30, 15, 46]],
      income: [-140, -320, 60], rma: RMA_RICE, gaps: 3,
      why: ['Keeps something growing in a year like 2022 instead of idle ground.', 'Safflower roots deep and needs roughly a third of the rice irrigation.', 'Leaves the field bare after July: the highest heat and autumn-rain exposure of the four.'],
      review: [['Local safflower buyer and contract', 'high'], ['Equipment: drill and combine header', 'medium'], ['Rice herbicide carryover to safflower', 'high']] }),
    strat({ id: 'car3_rice_wheat', loc: 'car_colusa_rice', name: 'Rice - winter wheat', short: 'Rice - winter wheat', line: 'Two-year cycle. Wheat year shown.', cycle: 2, shown: 'wheat year',
      calendar: [{ year: 1, crop_id: 'rice_medium_grain', plant: '05-10', harvest: '10-05', role: 'cash', timing_source: 'uc_rice_blog (V avg)' }, { year: 2, crop_id: 'winter_wheat', plant: '11-20', harvest: '06-15', role: 'cash', timing_source: 'fao56_table11 California December (V)' }],
      months: ['wheat', 'wheat', 'wheat', 'wheat', 'heading', 'harvest', 'bare', 'bare', 'bare', 'bare', 'drill wheat', 'wheat'], cover: 'cccccpbbbbpc',
      bare: [118, 95, 140], rain: [2, 0, 4], heat: [28, 20, 36], frost: [0, 0, 1],
      r22: [0, 210, 'Wheat finishes on winter rain plus one or two irrigations'], r23: [3, 90, 'Waterlogging risk for wheat on a poorly drained check'],
      etc: [470, 410, 540], need: [310, 230, 400],
      s: [[60, 50, 71], [12, 4, 22], [0, 0, 0], [55, 42, 68], [50, 40, 61], [70, 52, 84], [0, 0, 6], [44, 33, 55], [52, 38, 66]],
      income: [40, -90, 170], rma: RMA_RICE,
      why: ['Winter rain grows the wheat, so the two-year average irrigation is well below rice every year.', 'Rice and wheat are both grasses, so the pest-break score stays near zero.', 'Poorly drained soil (group D) is the main question for wheat.'],
      review: [['Drainage: wheat on a rice check', 'high'], ['Weedy rice and herbicide plan', 'medium']] }),
  ],
  caf_tulare_forage: [
    strat({ id: 'caf0_alfalfa', loc: 'caf_tulare_forage', base: true, name: 'Alfalfa, 7-8 cuts, 4-5 year stand', short: 'Current: alfalfa', line: 'What the field does now.', cycle: 5,
      calendar: [{ year: 1, crop_id: 'alfalfa', plant: '09-25', harvest: 'cuts Mar-Oct', role: 'forage', timing_source: 'uc_alfalfa (V)' }],
      months: ['dormant', 'growth', 'cut 1', 'cut 2', 'cut 3', 'cut 4', 'cut 5', 'cut 6', 'cut 7', 'cut 8', 'slow', 'dormant'], cover: 'pccccccccccp',
      bare: [6, 0, 14], rain: [0, 0, 1], heat: [0, 0, 2], frost: [0, 0, 1],
      r22: [0, 1290, 'Full pumping through the drought'], r23: [0, 1090, 'Wet spring trims early irrigations'],
      etc: [1280, 1150, 1400], need: [1210, 1060, 1370], openet: 1235,
      s: [[15, 8, 24], [92, 82, 98], [88, 75, 96], [80, 70, 90], [78, 68, 88], [70, 55, 84], [20, 10, 30], [82, 70, 92], [35, 22, 48]],
      income: [0, 0, 0], rma: RMA_FORAGE,
      why: ['This is the baseline every alternative is compared against.'], review: [['Allocation exceeded', 'high'], ['SGMA status', 'high']] }),
    strat({ id: 'caf1_grain_corn', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + silage corn', short: 'Small grain + corn', line: 'Typical dairy double crop.',
      calendar: [{ year: 1, crop_id: 'small_grain_silage', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'silage_corn', plant: '05-10', harvest: '09-05', role: 'forage', timing_source: 'assumed (U)' }],
      months: ['small grain', 'growth', 'growth', 'harvest silage', 'plant corn', 'corn', 'corn', 'corn harvest', 'bare', 'drill grain', 'grain', 'grain'], cover: 'cccppccpbpcc',
      bare: [44, 30, 60], rain: [1, 0, 2], heat: [3, 0, 7], frost: [0, 0, 1],
      r22: [0, 1080, 'Still above a 2.5 acre-ft/acre cap'], r23: [1, 900, 'Silage harvest window squeezed by spring rain'],
      etc: [1100, 980, 1230], need: [1010, 880, 1150],
      s: [[32, 22, 43], [95, 85, 100], [0, 0, 0], [58, 45, 70], [52, 42, 63], [82, 66, 94], [0, 0, 0], [46, 34, 58], [78, 64, 90]],
      income: [120, -60, 300], rma: RMA_FORAGE,
      why: ['Highest feed tonnage of the four, and it suits a herd that eats its own silage.', 'Saves roughly a sixth of the alfalfa irrigation in the model.', 'Fixes no nitrogen and both crops are grasses.'],
      review: [['Allocation exceeded', 'high'], ['Manure nitrogen plan', 'medium']] }),
    strat({ id: 'caf2_grain_sorghum', loc: 'caf_tulare_forage', name: 'Winter small-grain silage + sorghum-sudan', short: 'Small grain + sorghum-sudan', line: 'Lower-water summer forage than corn.',
      calendar: [{ year: 1, crop_id: 'small_grain_silage', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }, { year: 1, crop_id: 'sorghum_sudan', plant: '05-15', harvest: 'cuts Jun-Aug', role: 'forage', timing_source: 'assumed (U)' }],
      months: ['grain', 'growth', 'growth', 'harvest', 'plant sorghum-sudan', 'cut 1', 'cut 2', 'cut 3', 'terminate', 'drill grain', 'grain', 'grain'], cover: 'cccppcccppcc',
      bare: [30, 18, 44], rain: [1, 0, 2], heat: [2, 0, 5], frost: [0, 0, 1],
      r22: [0, 830, 'Close to the cap in a drought year'], r23: [1, 690, 'Under the cap'],
      etc: [880, 760, 1000], need: [770, 640, 910],
      s: [[52, 40, 64], [80, 68, 90], [0, 0, 0], [60, 47, 72], [54, 43, 65], [68, 50, 82], [0, 0, 0], [50, 38, 62], [78, 64, 90]],
      income: [60, -110, 230], rma: RMA_FORAGE, gaps: 3,
      why: ['Brings modelled irrigation need to about the 2.5 acre-ft/acre allocation.', 'Sorghum-sudan water savings versus corn are an extension position we still need to cite.', 'Feed quality is below corn silage; ration needs a nutritionist.'],
      review: [['Ration and feed quality', 'high'], ['Nitrate and prussic acid testing in forage', 'medium'], ['SGMA status', 'high']] }),
    strat({ id: 'caf3_short_alfalfa_break', loc: 'caf_tulare_forage', name: 'Shorter alfalfa stand + winter-cereal break', short: 'Short alfalfa + cereal break', line: 'Three-year stand, then an unirrigated summer. Break year shown.', cycle: 4, shown: 'break year',
      calendar: [{ year: 1, crop_id: 'alfalfa', plant: '09-25', harvest: 'cuts Mar-Oct', role: 'forage', timing_source: 'uc_alfalfa (V)' }, { year: 4, crop_id: 'winter_cereal', plant: '11-01', harvest: '04-25', role: 'forage', timing_source: 'assumed (U)' }],
      months: ['cereal', 'cereal', 'cereal', 'harvest silage', 'fallow', 'fallow', 'fallow', 'prep', 're-seed alfalfa', 'establishing', 'establishing', 'dormant'], cover: 'cccpbbbbpppp',
      bare: [36, 24, 50], rain: [0, 0, 1], heat: [9, 5, 13], frost: [0, 0, 1],
      r22: [0, 350, 'Break year: no summer pumping'], r23: [0, 260, 'Break year: no summer pumping'],
      etc: [450, 380, 530], need: [340, 250, 440],
      s: [[44, 33, 56], [74, 62, 85], [66, 52, 78], [62, 48, 74], [68, 56, 78], [62, 45, 76], [48, 34, 60], [70, 58, 81], [55, 42, 68]],
      income: [-40, -200, 130], rma: RMA_FORAGE,
      why: ['One summer in four with no irrigated crop is the point: it banks water under a pumping cap.', 'Keeps most of the nitrogen fixing and soil benefits of alfalfa.', 'Cycle-average irrigation is still above the allocation in alfalfa years.'],
      review: [['Allocation exceeded in alfalfa years', 'high'], ['Bare, hot summer in the break year', 'medium']] }),
  ],
};

// ---------------------------------------------------------------- news, models, BC card
const news = {
  car_colusa_rice: [
    { date: '2022-05-01', title: 'A Rough Year for Rice in California', source: 'NASA Earth Observatory', url: SOURCES.nasa_eo_rice.url, rank: 1, place_match: ['Sacramento Valley'], query_id: 'car_2022_drought', verified: true, signal: { dataset: 'smap_l3', label: 'SMAP soil moisture percentile', value_pct: 9, lead_days: null } },
    { date: '2022-05-20', title: 'Calif. rice acreage to drop to 39-year low', source: 'Farm Progress', url: SOURCES.farmprogress_rice.url, rank: 2, place_match: ['Sacramento Valley'], query_id: 'car_2022_drought', verified: true, signal: { dataset: 'smap_l3', label: 'SMAP soil moisture percentile', value_pct: 9, lead_days: null } },
    { date: '2023-01-09', title: 'Atmospheric rivers hit the Sacramento Valley (Jan-Mar 2023); late planting follows', source: 'headline to cache Saturday', url: null, rank: 3, place_match: ['Sacramento Valley', 'Colusa'], query_id: 'car_2023_storms', verified: false, signal: { dataset: 'imerg', label: 'IMERG 3-day rain percentile', value_pct: 97, lead_days: null } },
  ],
  caf_tulare_forage: [
    { date: '2023-03-20', title: 'Tulare Lake re-floods; about 114,000 acres under water at peak', source: 'headline to cache Saturday', url: null, rank: 3, place_match: ['Tulare Lake', 'Corcoran'], query_id: 'caf_2023_flood', verified: false, signal: { dataset: 'imerg', label: 'IMERG 3-day rain percentile', value_pct: 96, lead_days: null } },
    { date: '2024-04-16', title: 'State Water Board places Tulare Lake Subbasin on SGMA probation', source: 'State Water Resources Control Board', url: 'https://www.waterboards.ca.gov/sgma/', rank: 1, place_match: ['Tulare Lake Subbasin', 'Kings County'], query_id: 'caf_2024_probation', verified: true, signal: { dataset: 'grace', label: 'GRACE groundwater percentile', value_pct: 4, lead_days: null } },
    { date: '2022-07-15', title: '2021-22 drought: heavy groundwater pumping across the Tulare Lake bed', source: 'headline to cache Saturday', url: null, rank: 3, place_match: ['Kings County'], query_id: 'caf_2022_drought', verified: false, signal: { dataset: 'grace', label: 'GRACE groundwater percentile', value_pct: 3, lead_days: null } },
  ],
  bc: [
    { date: '2023-08-16', title: 'Fish population protection order: Salmon River and Bessette Creek', source: 'BC Gov News', url: SOURCES.bc_order.url, rank: 1, place_match: ['Salmon River', 'Bessette Creek'], query_id: 'bc_salmon_2023', verified: true, signal: null },
  ],
};

const models = {
  car_colusa_rice: [
    { id: 'bare_rule_car_v1', task: 'bare_cover', method: 'rule_ndvi', features: ['ndvi', 'bsi', 'ndwi'], labels: 'cdl_year_class + season_rules', split: { train_years: [], test_years: [2022, 2024, 2025] }, metrics: { accuracy: 0.88, f1_bare: 0.84, transition_mae_days: 11 }, notes: 'NDVI < 0.20 bare, 0.20-0.35 partial, > 0.35 covered. Illustrative metrics.' },
    { id: 'bare_rf_car_v1', task: 'bare_cover', method: 'random_forest', features: ['ndvi', 'bsi', 'ndwi', 'ndvi_slope_30d', 'doy'], labels: 'cdl_year_class + season_rules', split: { train_years: [2016, 2017, 2018, 2019, 2020, 2021, 2023], test_years: [2022, 2024, 2025] }, metrics: { accuracy: 0.92, f1_bare: 0.89, transition_mae_days: 8 }, disagreement_with: { rule_ndvi: 0.07 }, notes: '2022 (the fallow year) is held out. Spatial hold-out by field. Illustrative metrics.' },
  ],
  caf_tulare_forage: [
    { id: 'bare_rule_caf_v1', task: 'bare_cover', method: 'rule_ndvi', features: ['ndvi', 'bsi', 'ndwi'], labels: 'cdl_year_class + season_rules', split: { train_years: [], test_years: [2022, 2024, 2025] }, metrics: { accuracy: 0.9, f1_bare: 0.8, transition_mae_days: 9 }, notes: 'Illustrative metrics.' },
    { id: 'bare_rf_caf_v1', task: 'bare_cover', method: 'random_forest', features: ['ndvi', 'bsi', 'ndwi', 'ndvi_slope_30d', 'doy'], labels: 'cdl_year_class + season_rules', split: { train_years: [2016, 2017, 2018, 2019, 2020, 2021, 2023], test_years: [2022, 2024, 2025] }, metrics: { accuracy: 0.93, f1_bare: 0.86, transition_mae_days: 7 }, disagreement_with: { rule_ndvi: 0.06 }, notes: 'Illustrative metrics.' },
  ],
};

const bc = {
  id: 'bc_why_not_yet', name: 'Why not BC yet', place_line: 'Salmon River valley, Shuswap, British Columbia', centroid: { lon: -119.33, lat: 50.62 }, ground_data: 'thin',
  summary: 'BC is where this problem started for us, but no BC field is modelled, scored or validated here.',
  reasons: [
    { title: 'No OpenET', text: 'No field-scale measured water use to check our crop-water model against.' },
    { title: 'No field-soil API', text: 'No SSURGO equivalent; drainage and water-holding capacity would be guesses.' },
    { title: 'One station per valley', text: 'Too few weather stations to check satellite rain and ET.' },
    { title: 'Crop labels since 2011 only', text: 'AAFC Annual Crop Inventory is shorter than the US Cropland Data Layer (2008-).' },
  ],
  limits_line: 'BC is out of scope; transferability is a claim to test, not a result.',
  next_step: { label: 'Next step: BC data stack for a future version', items: ['SoilGrids v2', 'AAFC Annual Crop Inventory', 'ECCC stations', 'BC cover-crop factsheets (23 species)', 'BC Drought Portal'] },
  news: news.bc,
};

write('locations.json', locations);
write('strategies.json', strategies);
write('zones.json', { car_colusa_rice: cells('car_colusa_rice'), caf_tulare_forage: cells('caf_tulare_forage') });
write('year.json', { car_colusa_rice: yearData('car_colusa_rice'), caf_tulare_forage: yearData('caf_tulare_forage') });
write('trends.json', { car_colusa_rice: trends('car_colusa_rice'), caf_tulare_forage: trends('caf_tulare_forage') });
write('news.json', news);
write('models.json', models);
write('bc.json', bc);
write('sources.json', SOURCES);
console.log('mock data written to', OUT);
