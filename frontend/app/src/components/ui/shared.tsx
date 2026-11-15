// Building blocks for the farmer-first field panel and the printable brief.
// Rule of thumb (see .claude/skills/fieldshift-visual-design): lead with the grower's words and units,
// answer a question in a sentence, and put the satellite / pixel size / percentile in the "where this comes from" line.
import type { Calendar, FieldEvent, Location, RotationStrategy, WaterOrder } from '../../types';
import { BARE_DEF, observedBare, usuallyBareMonths } from '../../bare';
import type { ProvMap, Prov } from '../../api';
import { SOIL_COLOR, dateToT, fmtDate, haToAc, yearOf, dekadOf } from '../../lib';
const MONTHS_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
import Icon from '../Icons';
import type { ReactNode } from 'react';

const known = (s?: string | null) => !!(s && s.trim() && !/^(unknown|n\/?a|none)$/i.test(s.trim()));
/** Soil facts in plain words. Missing values return null. */
export function soilFacts(soil: Location['soil'] | null | undefined) {
  const s = soil ?? null;
  const td = s?.texture_detail;
  const ok = (x: unknown): x is number => typeof x === 'number' && isFinite(x);
  const mix = td && ok(td.sand_pct) && ok(td.silt_pct) && ok(td.clay_pct) ? { sand: td.sand_pct, silt: td.silt_pct, clay: td.clay_pct } : null;
  const texture = known(s?.texture_class) ? s!.texture_class.charAt(0).toUpperCase() + s!.texture_class.slice(1).toLowerCase() : null;
  const awc = s?.awc_mm_per_m?.value, inFt = ok(awc) ? (awc / 1000) * 12 : null;
  const dc = known(s?.drainage_class) ? s!.drainage_class.toLowerCase() : '', hg = known(s?.hydrologic_group) ? s!.hydrologic_group.toUpperCase().charAt(0) : '';
  const drain: 'slow' | 'fast' | 'well' | null = !dc && !hg ? null : hg === 'D' || /poorly|imperfectly/.test(dc) ? 'slow' : /excessive/.test(dc) || hg === 'A' ? 'fast' : 'well';
  const ec = ok(s?.ec_ds_per_m) ? s!.ec_ds_per_m! : null, salty = ec != null && ec >= 4;
  const clayey = (mix ? mix.clay >= 35 : false) || (/clay/.test(texture?.toLowerCase() ?? '') && !/sandy clay loam/.test(texture?.toLowerCase() ?? ''));
  const sandy = mix ? mix.sand >= 60 : /sand/.test(texture?.toLowerCase() ?? '');
  const rotation = salty ? 'Salt hurts some crops more than others; check salt tolerance with your adviser.'
    : clayey && (hg === 'C' || hg === 'D') && drain === 'slow' ? 'Clay holds water and drains slowly.'
    : sandy && inFt != null && inFt < 1.4 ? 'Sandy soil holds little water, so thirsty crops need more irrigation here.'
    : null;
  return {
    mix, texture,
    holds: inFt == null ? null : `Holds ${inFt.toFixed(1)} in of water per foot.${inFt < 1.4 ? ' Low.' : ''}`,
    drains: drain == null ? null : drain === 'slow' ? 'Drains slowly.' : drain === 'fast' ? 'Drains fast.' : 'Drains well.',
    salt: ec == null ? null : salty ? `Salty: ${ec.toFixed(1)} dS/m.` : 'Salt is low.',
    rotation,
    source: soilSourceName(s?.source?.id ?? s?.awc_mm_per_m?.source?.id),
  };
}
export function soilSourceName(id?: string | null) {
  const k = (id ?? '').toLowerCase();
  if (/illustrative/.test(k)) return 'Example soil until SoilGrids or a BC survey is wired';
  if (/aafc|slc/.test(k)) return 'AAFC Soil Landscapes of Canada (not field scale)';
  if (/soilgrids|isric/.test(k)) return 'SoilGrids (ISRIC), ~800 ft squares';
  if (/ssurgo|usda|nrcs/.test(k)) return 'USDA soil survey (SSURGO), top 3 feet';
  return 'Soil survey';
}
/** Sand / silt / clay stacked bar. */
export function SoilBar({ mix }: { mix: { sand: number; silt: number; clay: number } }) {
  const tot = mix.sand + mix.silt + mix.clay || 1;
  const parts = (['sand', 'silt', 'clay'] as const).map((k) => ({ k, w: (mix[k] / tot) * 100, pct: Math.round(mix[k]) }));
  return (
    <span className="soilbar" data-testid="soil-bar">
      <span className="sb-track" role="img" aria-label={parts.map((x) => `${x.k} ${x.pct}%`).join(', ')}>
        {parts.map((x) => <i key={x.k} style={{ width: `${x.w}%`, background: SOIL_COLOR[x.k] }} />)}
      </span>
      <span className="sb-key">{parts.map((x) => <span key={x.k}><i style={{ background: SOIL_COLOR[x.k] }} />{x.k.charAt(0).toUpperCase() + x.k.slice(1)} {x.pct}%</span>)}</span>
    </span>
  );
}
export const orderText = (o: WaterOrder) => o.kind === 'rescission' ? 'order rescinded'
  : `stop irrigating forage${o.licences ? ` (${o.licences} licences)` : ''}`;

export const isBC = (l: Location) => l.region_adapter === 'bc' || l.id.startsWith('bsr_');
export const fieldCode = (l: Location) => (l.dwr_id ? `DWR ${l.dwr_id}` : isBC(l) ? 'Illustrative BC field' : l.id.toUpperCase());
export const coords = (l: Location) => `${l.centroid.lat.toFixed(4)}° N, ${Math.abs(l.centroid.lon).toFixed(4)}° W`;
export const county = (l: Location) => l.county ?? (l.id === 'bsr_salmon_forage' ? 'Columbia-Shuswap' : 'Columbia-Shuswap');
/** "Columbia-Shuswap, British Columbia" vs "Kings County" — BC uses regional districts, not counties. */
export const placeLabel = (l: Location) => (isBC(l) ? `${county(l)}, British Columbia` : `${county(l)} County`);
export const acres = (l: Location) => Math.round(haToAc(l.area_ha.value));

/** Plain crop names: the Cropland Data Layer's own labels are not what a grower says. */
export const usd = (v: number) => (v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)} million` : `$${Math.round(v / 1000).toLocaleString()} thousand`);
export const cropName = (raw = '') => { const c = raw.replace(/\s*\(CDL pending\)/i, ''); return (
  c.startsWith('Fallow') ? 'Left fallow'
    : /pasture|forages?/i.test(c) ? 'Pasture and forages'
    : c.startsWith('Dbl Crop WinWht/Corn') ? 'Wheat, then corn'
    : c.startsWith('Dbl') ? c.replace('Dbl Crop ', '').replace('/', ', then ')
    : c || 'Not recorded'); };

const TOWNS: [string, number, number][] = [
  ['Salmon Arm', 50.7022, -119.2722], ['Enderby', 50.5508, -119.1397], ['Sicamous', 50.8369, -118.9867], ['Vernon', 50.267, -119.272],
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
  if (best.km > 60) return placeLabel(l);
  const mi = Math.max(1, Math.round(best.km * 0.621 * 2) / 2);
  const dir = DIRS[Math.round(((Math.atan2(best.dx, best.dy) * 180) / Math.PI + 360) % 360 / 45) % 8];
  return `${mi % 1 ? mi.toFixed(1) : mi} mile${mi === 1 ? '' : 's'} ${dir} of ${best.name}`;
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
  // live parts carry no status words; only example data (API not answering) is flagged
  if (!p || p.origin !== 'mock') return null;
  return <span className="src-tag mock" title={`${p.label}: ${p.detail}`}>Example numbers.</span>;
}

/** The satellites behind the field calendar, NASA first. */
export const calSource = (p?: Prov) => (/HLS/.test(p?.detail ?? '') ? 'NASA/USGS HLS satellites (Landsat and Sentinel-2, harmonised by NASA)' : 'Landsat (NASA/USGS) and Sentinel-2 satellites');

export type Step = 'drill' | 'year' | 'compare' | 'brief' | 'season';
/** Core path only. Map layers, 3D, year replay stay out of this flow until we add them back. */
export const FLOW: { n: number; id: Step | 'pick' | 'now'; label: string; short: string; does: string }[] = [
  { n: 1, id: 'pick', label: 'Pick your field', short: 'Pick', does: 'Choose the field' },
  { n: 2, id: 'now', label: 'Your field now', short: 'Now', does: 'Does today’s plan fit the water?' },
  { n: 3, id: 'season', label: 'Coming season', short: 'Season', does: 'What winter and next year look like' },
  { n: 4, id: 'compare', label: 'Compare rotations', short: 'Compare', does: 'What you’d gain or give up' },
  { n: 5, id: 'brief', label: 'Print for your adviser', short: 'Print', does: 'One page to take with you' },
];
/** Top of each step's panel: where you are, the step's name, and one sentence on why you are here.
 *  After the USWDS step indicator ("Step 2 of 5") and the GOV.UK one-question-per-page heading. */
export function StepHead({ id, title, purpose, children }: { id: (typeof FLOW)[number]['id']; title: string; purpose: ReactNode; children?: ReactNode }) {
  const i = FLOW.findIndex((s) => s.id === id);
  return (
    <header className="step-head" data-testid={`step-head-${id}`}>
      <p className="step-of">Step {i + 1} of {FLOW.length}</p>
      <ol className="step-bar" aria-hidden="true">{FLOW.map((s, k) => <li key={s.id} className={k < i ? 'done' : k === i ? 'on' : ''} />)}</ol>
      <h1>{title}</h1>
      <p className="step-purpose">{purpose}</p>
      {children}
    </header>
  );
}
/** Problem → what this tool does → goal. Shown on Pick; step list lives in the docked sidebar. */
export function Workflow({ current, problem, hideSteps }: { current: 'pick' | 'now' | 'season' | 'compare' | 'brief'; problem?: boolean; hideSteps?: boolean }) {
  const i = FLOW.findIndex((x) => x.id === current);
  return (
    <div className={`workflow ${problem ? 'wf-full' : 'wf-rail'}`} data-testid="workflow">
      {problem && (
        <div className="wf-brief" data-testid="wf-brief">
          <p>2023 cut forage water. Will your plan still fit?</p>
        </div>
      )}
      {!hideSteps && (
        <ol className="wf-steps" aria-label="Steps">
          {FLOW.map((s) => (
            <li key={s.id} className={s.id === current ? 'on' : i > FLOW.findIndex((x) => x.id === s.id) ? 'done' : ''} title={s.does}>
              <b>{s.n}</b><span>{s.short}</span>
            </li>
          ))}
        </ol>
      )}
      {!problem && !hideSteps && <p className="wf-step-hint">{FLOW[i]?.does}</p>}
    </div>
  );
}
/** One clear next step from Field now. */
export function Actions({ onStep }: { onStep: (s: Step) => void }) {
  return (
    <div className="actions one-next">
      <button className="action primary next-big" onClick={() => onStep('season')} data-testid="step-season">
        <span><b>Next: Coming season</b><small>Winter rain and whether next year still fits</small></span>
        <Icon name="right" size={18} />
      </button>
    </div>
  );
}

const when = (t: number) => { const d = dekadOf(t); return `${['early', 'mid', 'late'][d % 3]} ${MONTHS_FULL[Math.floor(d / 3)]}`; };
export function AboutField({ loc, prov, cal, insurance }: { loc: Location; prov: ProvMap; cal: Calendar | null; insurance: Location['rma'] | null }) {
  const rma = insurance;
  const ob = observedBare(cal), when = usuallyBareMonths(cal), dem = loc.nasadem;
  const s = loc.soil, saline = (s.ec_ds_per_m ?? 0) >= 4;
  const inFt = (s.awc_mm_per_m.value / 1000) * 12;
  return (
    <dl className="facts">
      <div><dt>Soil</dt><dd>{s.muname.split(',')[0]}{s.texture_class ? `, ${s.texture_class.toLowerCase()}` : ''} <cite><Src p={prov.soil} /></cite></dd></div>
      <div><dt>Holds</dt><dd>{inFt.toFixed(1)} in of water per foot of soil{inFt < 1.4 ? ' (low: needs frequent, short irrigations)' : inFt > 2 ? ' (high)' : ''}</dd></div>
      <div><dt>Drainage</dt><dd>{s.drainage_class}{s.hydrologic_group ? `; runoff group ${s.hydrologic_group}` : ''}</dd></div>
      <div><dt>Salt</dt><dd className={saline ? 'warn' : ''}>{s.ec_ds_per_m == null ? 'Not in the soil survey' : saline ? 'Salty soil; limits salt-sensitive crops' : 'Low salt'}{s.ec_ds_per_m != null && <small> (EC {s.ec_ds_per_m.toFixed(1)} dS/m)</small>}</dd></div>
      <div><dt>Water</dt><dd>{loc.water.source === 'surface' ? 'Surface water' : 'Groundwater (wells)'}{loc.water.district ? `, ${loc.water.district}` : !isBC(loc) ? <small className="na-line">; water district not looked up yet</small> : null}{!isBC(loc) && loc.water.sgma_subbasin ? `; ${loc.water.sgma_subbasin} subbasin` : ''}{isBC(loc) && loc.water.sgma_status?.text ? `. ${loc.water.sgma_status.text}` : ''}</dd></div>
      {dem?.slope_mean_pct != null && <div><dt>Slope</dt><dd>{dem.slope_mean_pct < 2 ? 'Nearly flat' : dem.slope_mean_pct < 5 ? 'Gentle slope' : 'Sloping'}, about {dem.slope_mean_pct.toFixed(1)}% on average{dem.low_spot_fraction ? `; low spots on about ${Math.round(dem.low_spot_fraction * 100)}% of the field, where water ponds and frost settles` : ''}. <cite>NASA NASADEM elevation, 100 ft squares; radar elevation reads 1 to 2% on a levelled field. <Src p={prov.terrain} /></cite></dd></div>}
      {rma && !isBC(loc) && <div><dt>Crop insurance</dt><dd>{usd(rma.total_usd)} paid out on {rma.scope} {rma.crop.replace('_forage', '').replace(/_/g, ' ')}, {rma.from}–{rma.to}; {usd(rma.top_usd)} in {rma.top_year} alone.{rma.share_drought >= 0.3 ? ` ${Math.round(rma.share_drought * 100)}% of it for drought or failed irrigation water.` : ''} <cite>USDA Risk Management Agency, county totals, not this farm. <Src p={prov.rma} /></cite></dd></div>}
      <div><dt>Usually bare</dt><dd>{ob ? <>About {ob.value} days a year, mostly {when} <cite>Seen by satellite, {ob.years[0]}–{ob.years[ob.years.length - 1]}. {BARE_DEF} <Src p={prov.calendar} /></cite></> : loc.observed_cover.summary}</dd></div>
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
      <cite>{isBC(loc) ? 'AAFC Annual Crop Inventory' : 'USDA Cropland Data Layer'} · <Src p={prov.crop_history} /></cite>
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
export function openetText(strategies: RotationStrategy[] | null | undefined, loc?: Location | null) {
  if (loc && isBC(loc)) return 'Crop water use from the rotation model with NASA POWER weather at this field.';
  const b = strategies?.find((s) => s.is_baseline), v = b?.water.etc_vs_openet_pct?.value;
  if (v == null) return 'Crop water use from the rotation model; not yet checked against a measured water-use product.';
  const r = Math.round(Math.abs(v));
  return `Checked against OpenET satellite measurements of this field: our estimate runs about ${r}% ${v >= 0 ? 'high' : 'low'}${v >= 0 ? ', as expected for a fully watered crop' : ''}.`;
}

/** The pick-list line, from the crop record: "Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022." */
export function recordLine(l: Location) {
  const ys = years(l).slice(-10), main = mainCrop(l);
  const n = ys.filter((y) => cropName(l.crop_history[y]).startsWith(main.split(',')[0])).length;
  const fallow = ys.filter((y) => cropName(l.crop_history[y]) === 'Left fallow');
  const list = (a: number[]) => (a.length > 1 ? `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}` : String(a[0]));
  return `${main.split(',')[0]} in ${n} of the last ${ys.length} years${fallow.length ? `; left fallow ${list(fallow)}` : ''}.`;
}
