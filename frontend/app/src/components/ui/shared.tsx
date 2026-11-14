// Building blocks shared by the three field-panel options (?ui=1|2|3).
// Deliberately not a place card: no hero photo, no round action buttons, no ratings. Readouts, record, method.
import type { Calendar, FieldEvent, Location, Regional } from '../../types';
import type { ProvMap, Prov } from '../../api';
import { CLASS_COLOR, CLASS_LABEL, GRACE_RAMP, SMAP_RAMP, dateToT, fieldState, fmtDate, haToAc, ordinal, ramp, tLabel } from '../../lib';
import Icon from '../Icons';

export const fieldCode = (l: Location) => (l.dwr_id ? `DWR ${l.dwr_id}` : l.id.toUpperCase());
export const coords = (l: Location) => `${l.centroid.lat.toFixed(4)}° N  ${Math.abs(l.centroid.lon).toFixed(4)}° W`;
export const county = (l: Location) => l.county ?? (l.id === 'car_colusa_rice' ? 'Colusa' : 'Kings');

export function Src({ p }: { p?: Prov }) {
  if (!p) return null;
  const t = p.origin === 'mock' ? 'mock' : p.origin === 'api' ? 'api' : 'file';
  return <span className={`src-tag ${t}`} title={`${p.label}: ${p.detail}${p.origin === 'file' ? ' (real output file; API route pending)' : ''}`}>{p.origin === 'mock' ? 'Mock data' : p.origin === 'api' ? 'Live' : 'Live · file'}</span>;
}

export type Step = 'drill' | 'year' | 'compare' | 'brief';
export const STEPS: { id: Step; n: string; label: string; sub: string }[] = [
  { id: 'drill', n: '01', label: 'Inspect layers', sub: 'surface → soil → groundwater' },
  { id: 'year', n: '02', label: 'Season record', sub: 'bare / covered / water, 2016–25' },
  { id: 'compare', n: '03', label: 'Compare rotations', sub: 'today vs 3 alternatives' },
  { id: 'brief', n: '04', label: 'Rotation brief', sub: 'printable, for the adviser' },
];
export function Workflow({ onStep, layout = 'list' }: { onStep: (s: Step) => void; layout?: 'list' | 'row' }) {
  return (
    <ol className={`workflow ${layout}`}>
      {STEPS.map((s) => (
        <li key={s.id}><button onClick={() => onStep(s.id)} data-testid={`step-${s.id}`}><em>{s.n}</em><span><b>{s.label}</b><small>{s.sub}</small></span><Icon name="right" size={14} /></button></li>
      ))}
    </ol>
  );
}

/** Instrument-style readouts for the scrubber date. */
export function Readouts({ cal, regional, t, detector, prov, compact }: { cal: Calendar | null; regional: Regional | null; t: number; detector: 'rule' | 'ml'; prov: ProvMap; compact?: boolean }) {
  const fs = cal ? fieldState(cal, t, detector) : null;
  const smap = regional?.smap_rootzone_pct.values[t] ?? null, grace = regional?.grace_gw_pct.values[t] ?? null;
  const rows = [
    { k: 'surface', sensor: 'Sentinel-2 / Landsat', scale: '10–30 m', what: 'Surface cover', val: fs ? CLASS_LABEL[fs.cls] : '…', sub: fs && fs.cls !== 'u' ? `NDVI ${fs.ndvi.toFixed(2)}` : 'no clear view', col: fs ? CLASS_COLOR[fs.cls] : '#555', gauge: fs ? Math.max(0, fs.ndvi) : 0, p: prov.calendar },
    { k: 'smap', sensor: 'SMAP L4', scale: '9 km', what: 'Root-zone moisture', val: smap == null ? 'no data' : `${ordinal(smap)} pct`, sub: 'vs same time of year', col: smap == null ? '#555' : ramp(SMAP_RAMP, smap), gauge: (smap ?? 0) / 100, p: prov.regional },
    { k: 'grace', sensor: 'GRACE-FO', scale: '0.25°', what: 'Groundwater storage', val: grace == null ? 'gap' : `${ordinal(grace)} pct`, sub: grace == null ? 'between missions' : 'basin context', col: grace == null ? '#555' : ramp(GRACE_RAMP, grace), gauge: (grace ?? 0) / 100, p: prov.regional },
  ];
  return (
    <div className={`readouts ${compact ? 'compact' : ''}`}>
      <div className="ro-head"><span>Readout</span><b>{tLabel(t)}</b></div>
      {rows.map((r) => (
        <div key={r.k} className="ro">
          <span className="ro-sensor">{r.sensor}<em>{r.scale}</em></span>
          <span className="ro-what">{r.what}</span>
          <span className="ro-val"><i style={{ background: r.col }} />{r.val}</span>
          <span className="ro-gauge"><i style={{ width: `${Math.round(r.gauge * 100)}%`, background: r.col }} /></span>
          <span className="ro-sub">{r.sub} <Src p={r.p} /></span>
        </div>
      ))}
    </div>
  );
}

export function SoilBlock({ loc, prov }: { loc: Location; prov: ProvMap }) {
  const s = loc.soil, td = s.texture_detail;
  const saline = (s.ec_ds_per_m ?? 0) >= 4;
  return (
    <div className="soil">
      <div className="sec-h"><span>Soil</span><small>SSURGO map unit</small><Src p={prov.soil} /></div>
      <b className="soil-name">{s.muname}</b>
      {td && (
        <div className="tex" title="0–100 cm weighted texture">
          <i style={{ width: `${td.sand_pct}%` }} className="sand">sand {Math.round(td.sand_pct)}%</i>
          <i style={{ width: `${td.silt_pct}%` }} className="silt">silt {Math.round(td.silt_pct)}</i>
          <i style={{ width: `${td.clay_pct}%` }} className="clay">clay {Math.round(td.clay_pct)}</i>
        </div>
      )}
      <dl className="kv">
        <div><dt>Texture</dt><dd>{s.texture_class}</dd></div>
        <div><dt>Hydrologic group</dt><dd>{s.hydrologic_group}</dd></div>
        <div><dt>Drainage</dt><dd>{s.drainage_class}</dd></div>
        <div><dt>Water holding</dt><dd>{Math.round(s.awc_mm_per_m.value)} mm/m <small>({((s.awc_mm_per_m.value / 1000) * 12).toFixed(1)} in/ft)</small></dd></div>
        {s.om_pct && <div><dt>Organic matter</dt><dd>{s.om_pct.value}%</dd></div>}
        {s.ec_ds_per_m != null && <div><dt>Salinity (EC)</dt><dd className={saline ? 'warn' : ''}>{s.ec_ds_per_m.toFixed(1)} dS/m{saline ? ' · saline' : ''}</dd></div>}
      </dl>
    </div>
  );
}

const CDL_CODE = (c = '') => (c.startsWith('Rice') ? ['R', '#4aa3ff'] : c.startsWith('Fallow') ? ['F', '#a8703f'] : c.startsWith('Alfalfa') ? ['A', '#3fbf6a'] : c.startsWith('Corn') ? ['C', '#e3c14f'] : c.startsWith('Dbl') ? ['W/C', '#c9a54a'] : [c.slice(0, 2), '#888']) as [string, string];
export function CropRecord({ loc, prov, from = 2008 }: { loc: Location; prov: ProvMap; from?: number }) {
  const years = Object.keys(loc.crop_history).map(Number).filter((y) => y >= from).sort();
  const crops = [...new Set(years.map((y) => loc.crop_history[y]))];
  return (
    <div className="record">
      <div className="sec-h"><span>Crop on record</span><small>USDA Cropland Data Layer</small><Src p={prov.crop_history} /></div>
      <div className="rec-row">
        {years.map((y) => { const [c, col] = CDL_CODE(loc.crop_history[y]); return <span key={y} title={`${y}: ${loc.crop_history[y]}`}><i style={{ background: col }}>{c}</i><em>{String(y).slice(2)}</em></span>; })}
      </div>
      <div className="rec-key">{crops.map((c) => { const [k, col] = CDL_CODE(c); return <span key={c}><i style={{ background: col }}>{k}</i>{c}</span>; })}</div>
    </div>
  );
}

export function EventLog({ events, setT }: { events: FieldEvent[]; setT: (t: number) => void }) {
  return (
    <div className="evlog">
      <div className="sec-h"><span>Event log</span><small>click to move the timeline</small></div>
      {events.map((e) => (
        <button key={e.date} onClick={() => setT(dateToT(e.date))}>
          <time>{fmtDate(e.date)}</time>
          <span><b>{e.title}</b>{e.detail && <small>{e.detail}</small>}</span>
          {e.url && <a href={e.url} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} title="Source"><Icon name="link" size={13} /></a>}
        </button>
      ))}
    </div>
  );
}

export function SiteFacts({ loc, prov }: { loc: Location; prov: ProvMap }) {
  return (
    <dl className="kv site">
      <div><dt>Outline</dt><dd>{loc.dwr_id ? `DWR / Land IQ 2023, field ${loc.dwr_id}` : 'placeholder square'} <Src p={prov.outline} /></dd></div>
      <div><dt>Area</dt><dd>{loc.area_ha.value.toFixed(1)} ha · {haToAc(loc.area_ha.value).toFixed(0)} ac</dd></div>
      <div><dt>Centroid</dt><dd className="mono">{coords(loc)}</dd></div>
      <div><dt>Water</dt><dd>{loc.water.source === 'surface' ? 'Surface water' : 'Groundwater'} · {loc.water.district} <Src p={prov.water} /></dd></div>
    </dl>
  );
}

/** Attribute-table field picker (replaces listing cards with thumbnails). */
export function FieldTable({ locations, selectedId, onSelect, onBC }: { locations: Location[]; selectedId: string | null; onSelect: (id: string) => void; onBC?: () => void }) {
  return (
    <table className="ftable" data-testid="field-table">
      <thead><tr><th>Field</th><th>County</th><th>2025 crop</th><th className="r">ha</th></tr></thead>
      <tbody>
        {locations.map((l) => (
          <tr key={l.id} className={selectedId === l.id ? 'on' : ''} onClick={() => onSelect(l.id)} data-testid={`row-${l.id}`}>
            <td><b className="mono">{fieldCode(l)}</b><small>{l.short_name}</small></td>
            <td>{county(l)}</td>
            <td>{l.crop_history['2025'] ?? '—'}</td>
            <td className="r mono">{l.area_ha.value.toFixed(1)}</td>
          </tr>
        ))}
        {onBC && <tr className="dim" onClick={onBC}><td><b className="mono">BC</b><small>Salmon River, Sumas Prairie</small></td><td colSpan={3}>not modelled yet: why</td></tr>}
      </tbody>
    </table>
  );
}

export function ProvList({ prov }: { prov: ProvMap }) {
  return (
    <ul className="provlist">
      {Object.values(prov).map((p) => <li key={p.part}><span>{p.label}</span><small>{p.detail}</small><Src p={p} /></li>)}
    </ul>
  );
}
