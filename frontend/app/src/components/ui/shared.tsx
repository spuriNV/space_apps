// Building blocks for the farmer-first field panel and the printable brief.
// Rule of thumb (see .claude/skills/fieldshift-visual-design): lead with the grower's words and units,
// answer a question in a sentence, and put the satellite / pixel size / percentile in the "where this comes from" line.
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import type { ProvMap, Prov } from '../../api';
import { dateToT, fieldState, fmtDate, haToAc, mmToAfac, ordinal, yearOf, dekadOf } from '../../lib';
const MONTHS_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
import Icon from '../Icons';

export const fieldCode = (l: Location) => (l.dwr_id ? `DWR ${l.dwr_id}` : l.id.toUpperCase());
export const coords = (l: Location) => `${l.centroid.lat.toFixed(4)}° N, ${Math.abs(l.centroid.lon).toFixed(4)}° W`;
export const county = (l: Location) => l.county ?? (l.id === 'car_colusa_rice' ? 'Colusa' : 'Kings');
export const acres = (l: Location) => Math.round(haToAc(l.area_ha.value));

/** Plain crop names: the Cropland Data Layer's own labels are not what a grower says. */
export const cropName = (c = '') =>
  c.startsWith('Fallow') ? 'Left fallow' : c.startsWith('Dbl Crop WinWht/Corn') ? 'Wheat, then corn' : c.startsWith('Dbl') ? c.replace('Dbl Crop ', '').replace('/', ', then ') : c || 'Not recorded';

const TOWNS: [string, number, number][] = [
  ['Williams', 39.1546, -122.1494], ['Colusa', 39.2143, -122.0094], ['Arbuckle', 39.0174, -122.0578], ['Maxwell', 39.2763, -122.1914],
  ['Hanford', 36.3275, -119.6457], ['Lemoore', 36.3008, -119.7829], ['Corcoran', 36.098, -119.5604], ['Stratford', 36.1897, -119.8232],
];
const DIRS = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
/** "3 miles east of Williams": nearest town from a short list, computed from the field centroid. */
export function nearTown(l: Location) {
  const { lat, lon } = l.centroid;
  let best = { name: '', km: 1e9, dx: 0, dy: 0 };
  for (const [name, tl, tn] of TOWNS) {
    const dx = (lon - tn) * 111.32 * Math.cos((lat * Math.PI) / 180), dy = (lat - tl) * 110.57, km = Math.hypot(dx, dy);
    if (km < best.km) best = { name, km, dx, dy };
  }
  if (best.km > 60) return `${county(l)} County`;
  const mi = Math.max(1, Math.round(best.km * 0.621));
  const dir = DIRS[Math.round(((Math.atan2(best.dx, best.dy) * 180) / Math.PI + 360) % 360 / 45) % 8];
  return `${mi} mile${mi === 1 ? '' : 's'} ${dir} of ${best.name}`;
}
const years = (l: Location) => Object.keys(l.crop_history).map(Number).sort();
export const latestCrop = (l: Location) => { const ys = years(l), y = ys[ys.length - 1]; return { year: y, crop: cropName(l.crop_history[y]) }; };
/** The crop the field is known for: most frequent non-fallow crop over the last 10 years on record. */
export function mainCrop(l: Location) {
  const n: Record<string, number> = {};
  years(l).slice(-10).forEach((y) => { const c = cropName(l.crop_history[y]); if (c !== 'Left fallow') n[c] = (n[c] ?? 0) + 1; });
  return Object.entries(n).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Crop';
}
export const fieldName = (l: Location) => `${mainCrop(l).split(',')[0]} field ${nearTown(l)}`;

/** Data status as words in the source line, not a pill: measured / from a saved run / example numbers. */
export function Src({ p }: { p?: Prov }) {
  if (!p) return null;
  const t = p.origin === 'mock' ? 'mock' : p.origin === 'api' ? 'api' : 'file';
  return <span className={`src-tag ${t}`} title={`${p.label}: ${p.detail}${p.origin === 'file' ? ' (real output file; API route pending)' : ''}`}>{p.origin === 'mock' ? 'Example numbers, not live yet.' : p.origin === 'api' ? 'Live.' : 'Live, from a saved run.'}</span>;
}

export type Step = 'drill' | 'year' | 'compare' | 'brief';
export const ACTIONS: { id: Step; label: string; sub: string }[] = [
  { id: 'year', label: 'See this field’s past 10 years', sub: 'When it was bare, green or flooded, 2016–2025' },
  { id: 'compare', label: 'Compare other rotations', sub: 'Water, soil and cover for today’s rotation and three others' },
  { id: 'drill', label: 'Look under the field', sub: 'Crop, soil moisture and groundwater as stacked layers' },
  { id: 'brief', label: 'Print a summary for your adviser', sub: 'One page, Letter size' },
];
export function Actions({ onStep }: { onStep: (s: Step) => void }) {
  return (
    <div className="actions">
      {ACTIONS.map((a) => (
        <button key={a.id} className={`action ${a.id === 'brief' ? 'primary' : ''}`} onClick={() => onStep(a.id)} data-testid={`step-${a.id}`}>
          <span><b>{a.label}</b><small>{a.sub}</small></span><Icon name="right" size={16} />
        </button>
      ))}
    </div>
  );
}

const when = (t: number) => { const d = dekadOf(t); return `${['early', 'mid', 'late'][d % 3]} ${MONTHS_FULL[Math.floor(d / 3)]}`; };
const GROUND: Record<string, [string, string]> = {
  c: ['A crop is growing, full green cover', 'good'], p: ['Thin or patchy cover', 'part'], b: ['Bare ground', 'bare'], w: ['Under water', 'water'], u: ['No clear satellite view (clouds)', 'none'],
};
const band = (pct: number, hi: string, mid: string, lo: string) => (pct >= 67 ? hi : pct > 33 ? mid : lo);

/** Three or four questions a grower would ask, answered for the timeline date. */
export function Answers(p: { loc: Location; cal: Calendar | null; regional: Regional | null; strategies: RotationStrategy[] | null; allocation?: number; t: number; detector: 'rule' | 'ml'; prov: ProvMap }) {
  const fs = p.cal ? fieldState(p.cal, p.t, p.detector) : null;
  const smap = p.regional?.smap_rootzone_pct.values[p.t] ?? null, grace = p.regional?.grace_gw_pct.values[p.t] ?? null;
  const base = p.strategies?.find((s) => s.is_baseline);
  const need = base ? mmToAfac(base.water.irrigation_need_mm.value) : null;
  const w = when(p.t);
  const g = fs ? GROUND[fs.cls] : null;
  return (
    <dl className="answers">
      <div className="ans">
        <dt>What is on the ground?</dt>
        <dd>
          <b><i className={`sw-${g?.[1] ?? 'none'}`} />{g ? g[0] : 'Loading…'}</b>
          {fs && fs.cls !== 'u' && fs.cls !== 'w' && <span>Greenness {fs.ndvi.toFixed(2)} (0 to 1; above 0.6 is a full canopy).</span>}
          <cite>Sentinel-2 and Landsat satellites, 10–30 m. <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>Is the soil wetter or drier than usual?</dt>
        <dd>
          <b>{smap == null ? 'No reading for this date' : band(smap, `Wetter than usual for ${w}`, `About normal for ${w}`, `Drier than usual for ${w}`)}</b>
          {smap != null && <span>{ordinal(Math.round(smap))} percentile (100 = wettest {w} since 2015).</span>}
          <cite>SMAP satellite, one 6-mile square around the field. <Src p={p.prov.regional} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>Is there more or less groundwater than usual?</dt>
        <dd>
          <b>{grace == null ? 'No reading: gap between satellite missions' : band(grace, 'More than usual in this basin', 'About normal in this basin', 'Less than usual in this basin')}</b>
          {grace != null && <span>{ordinal(Math.round(grace))} percentile. Whole basin, not your own well.</span>}
          <cite>GRACE-FO satellites, one 17-mile square. <Src p={p.prov.regional} /></cite>
        </dd>
      </div>
      {need != null && (
        <div className="ans">
          <dt>How much water does the current rotation need?</dt>
          <dd>
            <b>About {need.toFixed(1)} acre-feet per acre a year</b>
            <span>{p.allocation != null ? (need > p.allocation ? `Your limit is ${p.allocation.toFixed(1)}, so ${(need - p.allocation).toFixed(1)} short.` : `Fits your limit of ${p.allocation.toFixed(1)}.`) : ''} Today: {base!.name.replace(/ \(current\)/, '').split(',').slice(0, 2).join(',')}.</span>
            <cite>Rotation model: crop water use minus rain, {Math.round(base!.water.irrigation_need_mm.value / 25.4)} in a year. <Src p={p.prov.strategies} /></cite>
          </dd>
        </div>
      )}
    </dl>
  );
}

export function AboutField({ loc, prov }: { loc: Location; prov: ProvMap }) {
  const s = loc.soil, saline = (s.ec_ds_per_m ?? 0) >= 4;
  const inFt = (s.awc_mm_per_m.value / 1000) * 12;
  return (
    <dl className="facts">
      <div><dt>Soil</dt><dd>{s.muname.split(',')[0]} <cite><Src p={prov.soil} /></cite></dd></div>
      <div><dt>Holds</dt><dd>{inFt.toFixed(1)} in of water per foot of soil{inFt < 1.4 ? ' (low)' : inFt > 2 ? ' (high)' : ''}</dd></div>
      {s.ec_ds_per_m != null && <div><dt>Salt</dt><dd className={saline ? 'warn' : ''}>{saline ? 'Salty soil; limits salt-sensitive crops' : 'Low salt'} <small>(EC {s.ec_ds_per_m.toFixed(1)} dS/m)</small></dd></div>}
      <div><dt>Drainage</dt><dd>{s.drainage_class}</dd></div>
      <div><dt>Water</dt><dd>{loc.water.source === 'surface' ? 'Surface water' : 'Groundwater (wells)'} · {loc.water.district.replace(' (U)', '')} <cite><Src p={prov.water} /></cite></dd></div>
      <div><dt>Usually bare</dt><dd>{loc.observed_cover.summary}</dd></div>
    </dl>
  );
}

export const CROP_COL = (c: string) => (c.startsWith('Rice') ? '#3d7fc4' : c === 'Left fallow' ? '#b08a5a' : c.startsWith('Alfalfa') ? '#4f8f3a' : c.startsWith('Corn') ? '#d4b23c' : c.startsWith('Wheat') ? '#c79a3a' : '#8a8a80');
export function CropRecord({ loc, prov, from = 2016 }: { loc: Location; prov: ProvMap; from?: number }) {
  const ys = years(loc).filter((y) => y >= from);
  const crops = [...new Set(ys.map((y) => cropName(loc.crop_history[y])))];
  return (
    <div className="record">
      <div className="rec-row">
        {ys.map((y) => { const c = cropName(loc.crop_history[y]); return <span key={y} title={`${y}: ${c}`}><i style={{ background: CROP_COL(c) }} /><em>{y}</em></span>; })}
      </div>
      <div className="rec-key">{crops.map((c) => <span key={c}><i style={{ background: CROP_COL(c) }} />{c}</span>)}</div>
      <cite>USDA Cropland Data Layer · <Src p={prov.crop_history} /></cite>
    </div>
  );
}

export function EventLog({ events, setT }: { events: FieldEvent[]; setT: (t: number) => void }) {
  return (
    <div className="evlog">
      {events.map((e) => (
        <button key={e.date} onClick={() => setT(dateToT(e.date))} title="Move the timeline to this date">
          <time>{fmtDate(e.date)}</time>
          <span><b>{e.title}</b>{e.detail && <small>{e.detail}</small>}</span>
          {e.url && <a href={e.url} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} title="Source"><Icon name="link" size={13} /></a>}
        </button>
      ))}
    </div>
  );
}

export function ProvList({ prov }: { prov: ProvMap }) {
  return (
    <ul className="provlist">
      {Object.values(prov).map((p) => <li key={p.part}><span>{p.label}</span><small>{p.detail}</small><Src p={p} /></li>)}
    </ul>
  );
}

export const yearLabel = (t: number) => `${when(t)} ${yearOf(t)}`;
