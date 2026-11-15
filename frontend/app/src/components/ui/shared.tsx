// Building blocks for the farmer-first field panel and the printable brief.
// Rule of thumb (see .claude/skills/fieldshift-visual-design): lead with the grower's words and units,
// answer a question in a sentence, and put the satellite / pixel size / percentile in the "where this comes from" line.
import type { Calendar, DataGap, FieldEvent, Location, RotationStrategy, WaterOrder } from '../../types';
import { linkOf } from '../../types';
import { BARE_DEF, observedBare, usuallyBareMonths } from '../../bare';
import type { ProvMap, Prov } from '../../api';
import { SOIL_COLOR, dateToT, fmtDate, haToAc, yearOf, dekadOf } from '../../lib';
const MONTHS_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
import Icon from '../Icons';

export const fieldCode = (l: Location) => (l.dwr_id ? `DWR ${l.dwr_id}` : l.id.toUpperCase());
export const coords = (l: Location) => `${l.centroid.lat.toFixed(4)}° N, ${Math.abs(l.centroid.lon).toFixed(4)}° W`;
export const county = (l: Location) => l.county_name ?? l.county ?? (l.id === 'car_colusa_rice' ? 'Colusa' : 'Kings');
/** "Kings County" in California; "Columbia-Shuswap, BC" (a regional district) in British Columbia. */
export const place = (l: Location) => (l.region === 'bc' ? `${county(l)}, BC` : `${county(l)} County`);
/** The weather stations behind heat, frost and station rain. */
export const stationsName = (l: Location) => (l.region === 'bc' ? 'Environment Canada (ECCC) weather stations near the field' : 'NOAA weather stations near the field');
/** The yearly crop map. */
export const cropMapName = (l: Location) => (l.region === 'bc' ? 'AAFC Annual Crop Inventory (Agriculture Canada)' : 'USDA Cropland Data Layer');
/** Soil with the API's placeholders ("unknown", a pending SoilGrids name) blanked, for text that reads the fields directly. */
export const cleanSoil = (s: Location['soil'] | undefined): Location['soil'] => {
  const x = s ?? ({} as Location['soil']);
  return { ...x, muname: known(x.muname) && !/not fetched/i.test(x.muname) ? x.muname : '', texture_class: known(x.texture_class) ? x.texture_class : '',
    drainage_class: known(x.drainage_class) ? x.drainage_class : '', hydrologic_group: known(x.hydrologic_group) ? x.hydrologic_group : '' };
};
/** A value the API sends as a placeholder ("unknown", "pending") counts as missing. */
export const known = (x?: string | null) => !!x && !/^(unknown|pending|n\/a)$/i.test(x.trim());
export const acres = (l: Location) => Math.round(haToAc(l.area_ha.value));

/** Plain crop names: the Cropland Data Layer's own labels are not what a grower says. */
export const usd = (v: number) => (v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)} million` : `$${Math.round(v / 1000).toLocaleString()} thousand`);
export const cropName = (raw = '') => { const c = raw.replace(/\s*\(CDL pending\)/i, ''); return (
  c.startsWith('Pasture / Forages') ? 'Hay or pasture' : c.startsWith('Agriculture (undifferentiated)') ? 'Farmland, crop not identified' : c.startsWith('Not mapped') ? 'Not mapped' :
  c.startsWith('Fallow') ? 'Left fallow' : c.startsWith('Dbl Crop WinWht/Corn') ? 'Wheat, then corn' : c.startsWith('Dbl') ? c.replace('Dbl Crop ', '').replace('/', ', then ') : c || 'Not recorded'); };

const TOWNS: [string, number, number][] = [
  ['Williams', 39.1546, -122.1494], ['Colusa', 39.2143, -122.0094], ['Arbuckle', 39.0174, -122.0578], ['Maxwell', 39.2763, -122.1914],
  ['Hanford', 36.3275, -119.6457], ['Lemoore', 36.3008, -119.7829], ['Corcoran', 36.098, -119.5604], ['Stratford', 36.1897, -119.8232],
  ['Salmon Arm', 50.7001, -119.2838], ['Enderby', 50.5508, -119.1397],
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
  if (best.km > 60) return place(l);
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
/** BC: the grower's short name in miles ("Hay field 6 miles southwest of Salmon Arm"), not the API's longer km name. */
export const fieldName = (l: Location) => (l.region === 'bc' ? `${mainCrop(l).split(/,| or /)[0]} field ${nearTown(l)}` : l.farmer_name ?? `${mainCrop(l).split(',')[0]} field ${nearTown(l)}`);

/** Data status as words in the source line, not a pill: measured / from a saved run / example numbers. */
export function Src({ p }: { p?: Prov }) {
  // live parts carry no status words; only example data (API not answering) is flagged
  if (p?.origin === 'estimate') return <span className="src-tag est status estimate" title={`${p.label}: estimated, not measured on this field`}>Estimated.</span>;
  if (!p || p.origin !== 'mock') return null;
  return <span className="src-tag mock status example" title={`${p.label}: ${p.detail}`}>Example numbers.</span>;
}

/** The satellites behind the field calendar, NASA first. */
export const calSource = (p?: Prov) => (/HLS/.test(p?.detail ?? '') ? 'NASA/USGS HLS satellites (Landsat and Sentinel-2, harmonised by NASA)' : 'Landsat (NASA/USGS) and Sentinel-2 satellites');

/** BC: a California dataset this field lacks. `missing` = the route still answers 404: one quiet line where the panel would be.
 *  Otherwise the panel shows the API's estimate and this line (why, and what fills the gap) sits under More detail. */
export function GapLine({ gap, missing, className = '' }: { gap: DataGap | null; missing: boolean; className?: string }) {
  if (!gap) return null;
  if (missing) return <span className={`gap-line ${className}`} data-testid={`gap-${gap.id}`}>Not available in BC. {gap.reason}</span>;
  return <span className={`gap-line d-only ${className}`} data-testid={`gap-${gap.id}`}>{gap.reason}{gap.filled_with ? ` ${cap1(gap.filled_with)}${/[.]$/.test(cap1(gap.filled_with)) ? '' : '.'}` : ''}</span>;
}
// "(/insurance)" and similar API route names are for developers, not growers
const cap1 = (x: string) => { const y = x.replace(/\s*\((?:\/[\w?=&/_-]+(?:,\s*)?)+\)/g, ''); return y.charAt(0).toUpperCase() + y.slice(1); };

export type Step = 'drill' | 'year' | 'compare' | 'brief' | 'season';
export const ACTIONS: { id: Step; label: string; sub: string }[] = [
  { id: 'season', label: 'What’s likely this winter', sub: 'Rain, drought, reservoirs, bare weeks' },
  { id: 'year', label: 'This field’s year', sub: 'Bare, green or flooded, 2023–2026' },
  { id: 'compare', label: 'Compare rotations', sub: 'What you gain and give up' },
  { id: 'brief', label: 'Print for your adviser', sub: 'One page, Letter size' },
];
/** The one primary action of the field panel: a filled pill in the panel footer. */
export function PrimaryAction({ onStep }: { onStep: (s: Step) => void }) {
  return <button className="btn btn-primary btn-block" onClick={() => onStep('brief')} data-testid="step-brief"><Icon name="print" />{ACTIONS[3].label}</button>;
}
/** The other next steps as tappable rows with a chevron (they open a view), after the answers. */
export function NextSteps({ onStep }: { onStep: (s: Step) => void }) {
  return (
    <nav className="next-steps" aria-label="Next steps">
      {ACTIONS.filter((a) => a.id !== 'brief').map((a) => (
        <button key={a.id} className="nav-row" onClick={() => onStep(a.id)} data-testid={`step-${a.id}`}>
          <span>{a.label}</span><Icon name="right" size={20} />
        </button>
      ))}
    </nav>
  );
}
/** Phone: every next step as one sideways pill row under the sheet header, primary first. */
export function Actions({ onStep }: { onStep: (s: Step) => void }) {
  const order = [ACTIONS[3], ...ACTIONS.slice(0, 3)];
  return (
    <div className="sheet-actions" role="group" aria-label="Next steps">
      {order.map((a) => (
        <button key={a.id} className={`btn ${a.id === 'brief' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => onStep(a.id)} data-testid={`pill-${a.id}`}>
          {a.id === 'brief' && <Icon name="print" />}{a.label}
        </button>
      ))}
    </div>
  );
}

/** Soil facts in plain words, from the location route's soil (SSURGO; BC from AAFC Soil Landscapes of Canada, or SoilGrids). Missing values return null. */
export function soilFacts(soil: Location['soil'] | null | undefined) {
  const s = soil ?? null;
  const td = s?.texture_detail;
  const ok = (x: unknown): x is number => typeof x === 'number' && isFinite(x);
  const mix = td && ok(td.sand_pct) && ok(td.silt_pct) && ok(td.clay_pct) ? { sand: td.sand_pct, silt: td.silt_pct, clay: td.clay_pct } : null;
  const texture = known(s?.texture_class) ? s!.texture_class.charAt(0).toUpperCase() + s!.texture_class.slice(1).toLowerCase() : null;
  const awc = s?.awc_mm_per_m?.value, inFt = ok(awc) ? (awc / 1000) * 12 : null;
  const dc = known(s?.drainage_class) ? s!.drainage_class.toLowerCase() : '', hg = known(s?.hydrologic_group) ? s!.hydrologic_group.toUpperCase().charAt(0) : '';
  // imperfectly, somewhat poorly, poorly and very poorly drained all drain slowly, whatever the runoff group
  const drain: 'slow' | 'fast' | 'well' | null = !dc && !hg ? null : hg === 'D' || /poorly|imperfectly/.test(dc) ? 'slow' : /excessive/.test(dc) || hg === 'A' ? 'fast' : 'well';
  const ec = ok(s?.ec_ds_per_m) ? s!.ec_ds_per_m! : null, salty = ec != null && ec >= 4;
  const clayey = (mix ? mix.clay >= 35 : false) || /clay/.test(texture?.toLowerCase() ?? '') && !/sandy clay loam/.test(texture?.toLowerCase() ?? '');
  const sandy = (mix ? mix.sand >= 60 : /sand/.test(texture?.toLowerCase() ?? ''));
  const rotation = salty ? 'Salt hurts some crops more than others; check the crop’s salt tolerance with your adviser.'
    : clayey && (hg === 'C' || hg === 'D') && drain === 'slow' ? 'Clay holds water and drains slowly, so it suits flooded rice; slow drainage limits how much a rotation can improve infiltration.'
    : sandy && inFt != null && inFt < 1.4 ? 'Sandy soil holds little water, so crops that need steady moisture take more irrigation here, and flooded rice would lose water downward.'
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
/** The soil map behind the soil facts, from the soil's source id. */
export function soilSourceName(id?: string | null) {
  const k = (id ?? '').toLowerCase();
  if (/aafc|slc/.test(k)) return 'AAFC Soil Landscapes of Canada v3.2, a 1:1,000,000 map (not field scale)';
  if (/soilgrids|isric/.test(k)) return 'SoilGrids global soil model (ISRIC), 800 ft squares';
  if (/ssurgo|usda|nrcs/.test(k)) return 'USDA soil survey (SSURGO), top 3 feet';
  return 'Soil survey';
}
/** Sand / silt / clay as one stacked bar with a key underneath. */
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

/** One BC order in a few words, from its kind: an order to stop irrigating (with its licence count) or a rescission. */
export const orderText = (o: WaterOrder) => o.kind === 'rescission' ? 'order rescinded'
  : `order to stop irrigating forage${o.licences ? ` (${o.licences} licences)` : ''}${o.effective && o.effective !== o.date ? `, from ${fmtDate(o.effective)}` : ''}`;
/** Water source, district, GSA and groundwater-basin status from the looked-up location (empty values left out). */
export function WaterLine({ loc }: { loc: Location }) {
  const w = loc.water;
  const wc = loc.water_context;
  if (loc.region === 'bc') {
    // BC: no water district or groundwater basin; the watershed and the Province's irrigation orders instead
    if (!wc) return <small className="na-line">watershed not looked up yet</small>;
    return (
      <>{wc.watershed.split(';')[0]}.
        {wc.orders.map((o) => <span key={o.date + o.title} className="water-order"> {fmtDate(o.date)}: {orderText(o)}.{linkOf(o) && <> <a href={linkOf(o)!} target="_blank" rel="noreferrer">Source</a></>}</span>)}
      </>
    );
  }
  const src = w?.source === 'surface' ? 'Surface water' : w?.source === 'groundwater' ? 'Groundwater (wells)' : w?.source === 'mixed' ? 'Surface water and wells' : null;
  if (!loc.water_real) return <>{src}<small className="na-line">{src ? '; ' : ''}water district not looked up yet</small></>;
  const gsa = (Array.isArray(w.gsa) ? w.gsa : w.gsa ? [w.gsa] : []).filter(Boolean);
  const parts = [src, w.district, gsa.length ? `GSA: ${gsa.join(', ')}` : null].filter(Boolean);
  return (
    <>{parts.join('. ')}{parts.length ? '.' : ''}
      {w.sgma_status?.text && <span className="water-sgma"> {w.sgma_status.text}.</span>}
      {linkOf(w.sgma_status) && <> <a href={linkOf(w.sgma_status)!} target="_blank" rel="noreferrer">Source</a></>}
    </>
  );
}

const CAUSE: Record<string, string> = { drought: 'drought', excess_moisture: 'too much water', heat: 'heat', other: 'frost and other', frost_other: 'frost and other', frost: 'frost', cold: 'cold' };
const when = (t: number) => { const d = dekadOf(t); return `${['early', 'mid', 'late'][d % 3]} ${MONTHS_FULL[Math.floor(d / 3)]}`; };
export function AboutField({ loc, prov, cal, insurance, insGap }: { loc: Location; prov: ProvMap; cal: Calendar | null; insurance: Location['rma'] | null; insGap?: DataGap | null }) {
  const rma = insurance;
  const ob = observedBare(cal), when = usuallyBareMonths(cal), dem = loc.nasadem;
  const s = loc.soil ?? ({} as Partial<Location['soil']>), saline = (s.ec_ds_per_m ?? 0) >= 4;
  const awc = s.awc_mm_per_m?.value, inFt = awc != null ? (awc / 1000) * 12 : null;
  // placeholders ("unknown", a soil name that only says the fetch is pending) are left out
  const mu = known(s.muname) && !/not fetched/i.test(s.muname ?? '') && (s as { mukey?: string }).mukey !== 'pending' ? s.muname! : '';
  const tex = known(s.texture_class) ? s.texture_class! : '', dc = known(s.drainage_class) ? s.drainage_class! : '', hg = known(s.hydrologic_group) ? s.hydrologic_group! : '';
  return (
    <dl className="facts">
      {(mu || tex) && <div><dt>Soil</dt><dd>{mu ? mu.split(',')[0] : ''}{tex ? `${mu ? ', ' : ''}${tex.toLowerCase()}` : ''} <cite><Src p={prov.soil} /></cite></dd></div>}
      {inFt != null && <div><dt>Holds</dt><dd>{inFt.toFixed(1)} in of water per foot of soil{inFt < 1.4 ? ' (low: needs frequent, short irrigations)' : inFt > 2 ? ' (high)' : ''}</dd></div>}
      {(dc || hg) && <div><dt>Drainage</dt><dd>{dc}{hg ? `${dc ? '; ' : ''}runoff group ${hg}` : ''}</dd></div>}
      {s.ec_ds_per_m != null && <div><dt>Salt</dt><dd className={saline ? 'warn' : ''}>{saline ? 'Salty soil; limits salt-sensitive crops' : 'Low salt'}<small> (EC {s.ec_ds_per_m.toFixed(1)} dS/m)</small></dd></div>}
      <div><dt>{loc.region === 'bc' ? 'Watershed' : 'Water'}</dt><dd><WaterLine loc={loc} /></dd></div>
      {dem?.slope_mean_pct != null && <div><dt>Slope</dt><dd>{dem.slope_mean_pct < 2 ? 'Nearly flat' : dem.slope_mean_pct < 5 ? 'Gentle slope' : 'Sloping'}, about {dem.slope_mean_pct.toFixed(1)}% on average{dem.low_spot_fraction ? `; low spots on about ${Math.round(dem.low_spot_fraction * 100)}% of the field, where water ponds and frost settles` : ''}. <cite>NASA NASADEM elevation, 100 ft squares; radar elevation reads 1 to 2% on a levelled field. <Src p={prov.terrain} /></cite></dd></div>}
      {!rma && insGap && <div><dt>Crop insurance</dt><dd><GapLine gap={insGap} missing /></dd></div>}
      {rma && rma.total_usd == null && <div><dt>Crop losses</dt><dd>Usual causes of crop loss here: {(rma.shares ?? []).map((x) => `${CAUSE[x.cause] ?? x.cause.replace(/_/g, ' ')} ${Math.round(x.share * 100)}%`).join(', ')}. No dollar figures. <cite><Src p={prov.rma} /></cite>{insGap && <GapLine gap={insGap} missing={false} />}</dd></div>}
      {rma && rma.total_usd != null && <div><dt>Crop insurance</dt><dd>{usd(rma.total_usd)} paid out on {rma.scope} {rma.crop.replace('_forage', '').replace(/_/g, ' ')}, {rma.from}–{rma.to}; {usd(rma.top_usd)} in {rma.top_year} alone.{rma.share_drought >= 0.3 ? ` ${Math.round(rma.share_drought * 100)}% of it for drought or failed irrigation water.` : ''} <cite>USDA Risk Management Agency, county totals, not this farm. <Src p={prov.rma} /></cite>{insGap && <GapLine gap={insGap} missing={false} />}</dd></div>}
      <div><dt>Usually bare</dt><dd>{ob ? <>About {ob.value} days a year, mostly {when} <cite>Seen by satellite, {ob.years[0]}–{ob.years[ob.years.length - 1]}. {BARE_DEF} <Src p={prov.calendar} /></cite></> : loc.observed_cover.summary}</dd></div>
    </dl>
  );
}

export const CROP_COL = (c: string) => (c.startsWith('Rice') ? '#3d7fc4' : c === 'Left fallow' ? '#b08a5a' : c.startsWith('Alfalfa') || c.startsWith('Hay') ? '#4f8f3a' : c.startsWith('Corn') ? '#d4b23c' : c.startsWith('Wheat') ? '#c79a3a' : '#8a8a80');
export function CropRecord({ loc, prov, from = 2016 }: { loc: Location; prov: ProvMap; from?: number }) {
  const ys = years(loc).filter((y) => y >= from);
  const crops = [...new Set(ys.map((y) => cropName(loc.crop_history[y])))];
  return (
    <div className="record">
      <div className="rec-row">
        {ys.map((y) => { const c = cropName(loc.crop_history[y]); return <span key={y} title={`${y}: ${c}`}><i style={{ background: CROP_COL(c) }} /><em>{y}</em></span>; })}
      </div>
      <div className="rec-key">{crops.map((c) => <span key={c}><i style={{ background: CROP_COL(c) }} />{c}</span>)}</div>
      <cite>{cropMapName(loc)} · <Src p={prov.crop_history} /></cite>
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
          {linkOf(e) && <a href={linkOf(e)!} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} title="Source"><Icon name="link" size={13} /></a>}
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

/** The pick-list line, from the crop record: "Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022." */
export function recordLine(l: Location) {
  const ys = years(l).slice(-10), main = mainCrop(l);
  const n = ys.filter((y) => cropName(l.crop_history[y]).startsWith(main.split(',')[0])).length;
  const fallow = ys.filter((y) => cropName(l.crop_history[y]) === 'Left fallow');
  const list = (a: number[]) => (a.length > 1 ? `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}` : String(a[0]));
  return `${main.split(',')[0]} in ${n} of the last ${ys.length} years${fallow.length ? `; left fallow ${list(fallow)}` : ''}.`;
}
