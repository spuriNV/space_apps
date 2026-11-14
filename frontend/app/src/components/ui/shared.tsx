// Building blocks for the farmer-first field panel and the printable brief.
// Rule of thumb (see .claude/skills/fieldshift-visual-design): lead with the grower's words and units,
// answer a question in a sentence, and put the satellite / pixel size / percentile in the "where this comes from" line.
import type { FieldEvent, Location, RotationStrategy } from '../../types';
import type { ProvMap, Prov } from '../../api';
import { dateToT, fmtDate, haToAc, yearOf, dekadOf } from '../../lib';
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

export type Step = 'drill' | 'year' | 'compare' | 'brief' | 'season';
export const ACTIONS: { id: Step; label: string; sub: string }[] = [
  { id: 'season', label: 'What’s likely this winter', sub: 'Rain, drought, reservoirs, bare weeks' },
  { id: 'year', label: 'This field’s year', sub: 'Bare, green or flooded, 2023–2026' },
  { id: 'compare', label: 'Compare rotations', sub: 'What you gain and give up' },
  { id: 'brief', label: 'Print for your adviser', sub: 'One page, Letter size' },
];
export function Actions({ onStep }: { onStep: (s: Step) => void }) {
  return (
    <div className="actions">
      {ACTIONS.map((a) => (
        <button key={a.id} className={`action ${a.id === 'brief' ? 'primary' : ''}`} onClick={() => onStep(a.id)} data-testid={`step-${a.id}`}>
          <span><b>{a.label}</b><small>{a.sub}</small></span>
        </button>
      ))}
    </div>
  );
}

const when = (t: number) => { const d = dekadOf(t); return `${['early', 'mid', 'late'][d % 3]} ${MONTHS_FULL[Math.floor(d / 3)]}`; };
export function AboutField({ loc, prov }: { loc: Location; prov: ProvMap }) {
  const s = loc.soil, saline = (s.ec_ds_per_m ?? 0) >= 4;
  const inFt = (s.awc_mm_per_m.value / 1000) * 12;
  return (
    <dl className="facts">
      <div><dt>Soil</dt><dd>{s.muname.split(',')[0]}{s.texture_class ? `, ${s.texture_class.toLowerCase()}` : ''} <cite><Src p={prov.soil} /></cite></dd></div>
      <div><dt>Holds</dt><dd>{inFt.toFixed(1)} in of water per foot of soil{inFt < 1.4 ? ' (low: needs frequent, short irrigations)' : inFt > 2 ? ' (high)' : ''}</dd></div>
      <div><dt>Drainage</dt><dd>{s.drainage_class}{s.hydrologic_group ? `; runoff group ${s.hydrologic_group}` : ''}</dd></div>
      <div><dt>Salt</dt><dd className={saline ? 'warn' : ''}>{s.ec_ds_per_m == null ? 'Not in the soil survey' : saline ? 'Salty soil; limits salt-sensitive crops' : 'Low salt'}{s.ec_ds_per_m != null && <small> (EC {s.ec_ds_per_m.toFixed(1)} dS/m)</small>}</dd></div>
      <div><dt>Water</dt><dd>{loc.water.source === 'surface' ? 'Surface water' : 'Groundwater (wells)'}, {loc.water.district.replace(' (U)', '')} <cite><Src p={prov.water} /></cite></dd></div>
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

/** Honest line on how the water model compares with OpenET measured water use on this field (baseline crop years only). */
export function openetText(strategies: RotationStrategy[] | null | undefined) {
  const b = strategies?.find((s) => s.is_baseline), v = b?.water.etc_vs_openet_pct?.value;
  if (v == null) return 'Not yet checked against measured water use (OpenET).';
  const r = Math.round(Math.abs(v));
  return `Checked against OpenET satellite measurements of this field: our estimate runs about ${r}% ${v >= 0 ? 'high' : 'low'}${v >= 0 ? ', as expected for a fully watered crop' : ''}.`;
}
