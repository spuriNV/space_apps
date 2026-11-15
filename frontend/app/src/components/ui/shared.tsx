// Building blocks for the farmer-first field panel and the printable brief.
// Rule of thumb (see .claude/skills/fieldshift-visual-design): lead with the grower's words and units,
// answer a question in a sentence, and put the satellite / pixel size / percentile in the "where this comes from" line.
import type { Calendar, DataGap, FieldEvent, Location, RotationStrategy, WaterOrder } from '../../types';
import { linkOf } from '../../types';
import { BARE_DEF, observedBare, usuallyBareMonths } from '../../bare';
import type { ProvMap, Prov } from '../../api';
import { SOIL_COLOR, dateToT, fmtDate, haToAc, yearOf, dekadOf } from '../../lib';
import { t, tx, isEs, locale } from '../../i18n';
import Icon from '../Icons';

export const fieldCode = (l: Location) => (l.dwr_id ? `DWR ${l.dwr_id}` : l.id.toUpperCase());
/** "State field no. 123" for a DWR field code, else the id (lower-cased by the brief). */
export const stateFieldNo = (l: Location) => fieldCode(l).replace('DWR ', `${t('ui.statefield')} `);
export const coords = (l: Location) => `${Math.abs(l.centroid.lat).toFixed(4)}° ${l.centroid.lat >= 0 ? t('ui.dir.N') : t('ui.dir.S')}, ${Math.abs(l.centroid.lon).toFixed(4)}° ${l.centroid.lon < 0 ? t('ui.dir.W') : t('ui.dir.E')}`;
export const county = (l: Location) => l.county_name ?? l.county ?? (l.id === 'car_colusa_rice' ? 'Colusa' : 'Kings');
/** "Kings County" in California; "Columbia-Shuswap, BC" (a regional district) in British Columbia. */
export const place = (l: Location) => (l.spot ? spotPlace(l) : l.region === 'bc' ? `${county(l)}, BC` : t('ui.place.county', { name: county(l) }));
/** A tapped spot's place: its county (and state outside California), or the coordinates when no US county was found. */
const spotPlace = (l: Location) => (l.region === 'bc'
  ? `${(l as { regional_district?: string | null }).regional_district || l.county_name || t('ui.place.bc')}, BC`
  : l.county_name ? `${t('ui.place.county', { name: l.county_name })}${l.state_code && l.state_code !== 'CA' ? `, ${l.state_code}` : ''}` : l.spot?.state === 'ready' ? t('ui.place.outside') : t('ui.place.finding'));
/** The weather stations behind heat, frost and station rain. */
export const stationsName = (l: Location) => (l.region === 'bc' ? t('ui.stations.bc') : t('ui.stations.ca'));
/** The yearly crop map. */
export const cropMapName = (l: Location) => (l.region === 'bc' ? t('ui.cropmap.bc') : t('ui.cropmap.ca'));
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
export const usd = (v: number) => (v >= 1e6 ? t('ui.usd.million', { n: (v / 1e6).toFixed(v >= 1e8 ? 0 : 1) }) : t('ui.usd.thousand', { n: Math.round(v / 1000).toLocaleString(locale) }));
export const cropKey = (raw = '') => { const c = raw.replace(/\s*\(CDL pending\)/i, ''); return (
  c.startsWith('Pasture / Forages') ? 'Hay or pasture' : c.startsWith('Agriculture (undifferentiated)') ? 'Farmland, crop not identified' : c.startsWith('Not mapped') ? 'Not mapped' :
  c.startsWith('Fallow') ? 'Left fallow' : c.startsWith('Dbl Crop WinWht/Corn') ? 'Wheat, then corn' : c.startsWith('Dbl') ? c.replace('Dbl Crop ', '').replace('/', ', then ') : c || 'Not recorded'); };
/** The crop's name for display (Spanish in Spanish mode); `cropKey` stays English for comparisons and colours. */
export const cropName = (raw = '') => { const k = cropKey(raw), whole = tx(k); return whole !== k || !k.includes(', then ') ? whole : k.split(', then ').map(tx).join(t('ui.then')); };

const TOWNS: [string, number, number][] = [
  ['Williams', 39.1546, -122.1494], ['Colusa', 39.2143, -122.0094], ['Arbuckle', 39.0174, -122.0578], ['Maxwell', 39.2763, -122.1914],
  ['Hanford', 36.3275, -119.6457], ['Lemoore', 36.3008, -119.7829], ['Corcoran', 36.098, -119.5604], ['Stratford', 36.1897, -119.8232],
  ['Salmon Arm', 50.7001, -119.2838], ['Enderby', 50.5508, -119.1397],
];
const DIRS = () => ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'].map((d) => t(`ui.dir.${d}`));
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
  const dir = DIRS()[Math.round(((Math.atan2(best.dx, best.dy) * 180) / Math.PI + 360) % 360 / 45) % 8];
  return t(mi === 1 ? 'ui.near.one' : 'ui.near.many', { mi: mi % 1 ? mi.toFixed(1) : mi, dir, name: best.name });
}
const years = (l: Location) => Object.keys(l.crop_history).map(Number).sort();
export const latestCrop = (l: Location) => { const ys = years(l), y = ys[ys.length - 1]; return { year: y, crop: cropName(l.crop_history[y]), key: cropKey(l.crop_history[y]) }; };
/** The crop the field is known for: most frequent non-fallow crop over the last 10 years on record. */
export function mainCrop(l: Location) {
  const n: Record<string, number> = {};
  years(l).slice(-10).forEach((y) => { const c = cropKey(l.crop_history[y]); if (c !== 'Left fallow') n[c] = (n[c] ?? 0) + 1; });
  return Object.entries(n).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Crop';
}
/** BC: the grower's short name in miles ("Hay field 6 miles southwest of Salmon Arm"), not the API's longer km name. */
const cropWord = (c: string) => (isEs ? tx(c).toLowerCase() : c);
export const fieldName = (l: Location) => (l.region === 'bc' ? t('ui.field.name', { crop: cropWord(mainCrop(l).split(/,| or /)[0]), near: nearTown(l) }) : l.farmer_name ?? t('ui.field.name', { crop: cropWord(mainCrop(l).split(',')[0]), near: nearTown(l) }));

/** Data status as words in the source line, not a pill: measured / from a saved run / example numbers. */
export function Src({ p }: { p?: Prov }) {
  // live parts carry no status words; only example data (API not answering) is flagged
  if (p?.origin === 'estimate') return <span className="src-tag est status estimate" title={t('ui.src.est_title', { label: p.label })}>{t('ui.src.est')}</span>;
  if (!p || p.origin !== 'mock') return null;
  return <span className="src-tag mock status example" title={`${p.label}: ${p.detail}`}>{t('ui.src.example')}</span>;
}

/** The satellites behind the field calendar, NASA first. */
export const calSource = (p?: Prov) => (/HLS/.test(p?.detail ?? '') ? t('ui.cal.hls') : t('ui.cal.ls'));
/** The same without the word "satellites" (for "Greenness from ..."). */
export const calSourceShort = (p?: Prov) => (/HLS/.test(p?.detail ?? '') ? t('ui.cal.hls_short') : t('ui.cal.ls_short'));

/** BC: a California dataset this field lacks. `missing` = the route still answers 404: one quiet line where the panel would be.
 *  Otherwise the panel shows the API's estimate and this line (why, and what fills the gap) sits under More detail. */
export function GapLine({ gap, missing, className = '' }: { gap: DataGap | null; missing: boolean; className?: string }) {
  if (!gap) return null;
  if (missing) return <span className={`gap-line ${className}`} data-testid={`gap-${gap.id}`}>{t('ui.gap.bc')} {gap.reason}</span>;
  return <span className={`gap-line d-only ${className}`} data-testid={`gap-${gap.id}`}>{gap.reason}{gap.filled_with ? ` ${cap1(gap.filled_with)}${/[.]$/.test(cap1(gap.filled_with)) ? '' : '.'}` : ''}</span>;
}
// "(/insurance)" and similar API route names are for developers, not growers
const cap1 = (x: string) => { const y = x.replace(/\s*\((?:\/[\w?=&/_-]+(?:,\s*)?)+\)/g, ''); return y.charAt(0).toUpperCase() + y.slice(1); };

export type Step = 'drill' | 'year' | 'compare' | 'brief' | 'season';
export type FlowId = 'pick' | 'now' | 'season' | 'compare' | 'brief';
/** The numbered path (from the sp branch): one step per screen, steps 2 to 5 locked until a field is picked. */
export const FLOW: { n: number; id: FlowId; label: string; short: string; does: string }[] = [
  { n: 1, id: 'pick', label: t('ui.flow.pick.label'), short: t('ui.flow.pick.short'), does: t('ui.flow.pick.does') },
  { n: 2, id: 'now', label: t('ui.flow.now.label'), short: t('ui.flow.now.short'), does: t('ui.flow.now.does') },
  { n: 3, id: 'season', label: t('ui.flow.season.label'), short: t('ui.flow.season.short'), does: t('ui.flow.season.does') },
  { n: 4, id: 'compare', label: t('ui.flow.compare.label'), short: t('ui.flow.compare.short'), does: t('ui.flow.compare.does') },
  { n: 5, id: 'brief', label: t('ui.flow.brief.label'), short: t('ui.flow.brief.short'), does: t('ui.flow.brief.does') },
];
/** Top of each step's screen: where you are ("Step 2 of 5", with a 5-segment bar) and one sentence on what the step is for.
 *  After the USWDS step indicator and the GOV.UK one-question-per-page heading. */
export function StepLine({ id, purpose }: { id: FlowId; purpose?: string }) {
  const i = FLOW.findIndex((s) => s.id === id);
  return (
    <div className="step-line" data-testid={`step-line-${id}`}>
      <p className="step-of">
        <b>{t('ui.step.of', { n: i + 1, total: FLOW.length })}</b>
        <span className="step-bar" aria-hidden="true">{FLOW.map((s, k) => <i key={s.id} className={k < i ? 'done' : k === i ? 'on' : ''} />)}</span>
      </p>
      {purpose && <p className="step-purpose">{purpose}</p>}
    </div>
  );
}
/** Problem, what this tool does, goal. Shown on Pick. */
export function Workflow() {
  const rows: [string, string][] = [
    [t('ui.wf.problem'), t('ui.wf.problem_t')],
    [t('ui.wf.does'), t('ui.wf.does_t')],
    [t('ui.wf.goal'), t('ui.wf.goal_t')],
  ];
  return (
    <dl className="workflow" data-testid="workflow">
      {rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
    </dl>
  );
}
export const ACTIONS: { id: Step; label: string; sub: string }[] = [
  { id: 'season', label: t('ui.act.season'), sub: t('ui.act.season_s') },
  { id: 'year', label: t('ui.act.year'), sub: t('ui.act.year_s') },
  { id: 'drill', label: t('ui.act.drill'), sub: t('ui.act.drill_s') },
  { id: 'compare', label: t('ui.act.compare'), sub: t('ui.act.compare_s') },
  { id: 'brief', label: t('ui.act.brief'), sub: t('ui.act.brief_s') },
];
const brief = () => ACTIONS.find((a) => a.id === 'brief')!;
/** The one primary action of the field panel: a filled pill in the panel footer. */
export function PrimaryAction({ onStep }: { onStep: (s: Step) => void }) {
  return <button className="btn btn-primary btn-block" onClick={() => onStep('brief')} data-testid="step-brief"><Icon name="print" />{brief().label}</button>;
}
/** The other next steps as tappable rows with a chevron (they open a view), after the answers. */
export function NextSteps({ onStep }: { onStep: (s: Step) => void }) {
  return (
    <nav className="next-steps" aria-label={t('ui.act.next')}>
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
  const order = [brief(), ...ACTIONS.filter((a) => a.id !== 'brief')];
  return (
    <div className="sheet-actions" role="group" aria-label={t('ui.act.next')}>
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
  const rotation = salty ? t('ui.soil.rot_salt')
    : clayey && (hg === 'C' || hg === 'D') && drain === 'slow' ? t('ui.soil.rot_clay')
    : sandy && inFt != null && inFt < 1.4 ? t('ui.soil.rot_sand')
    : null;
  return {
    mix, texture,
    holds: inFt == null ? null : `${t('ui.soil.holds', { n: inFt.toFixed(1) })}${inFt < 1.4 ? ` ${t('ui.soil.low')}` : ''}`,
    drains: drain == null ? null : drain === 'slow' ? t('ui.soil.drain_slow') : drain === 'fast' ? t('ui.soil.drain_fast') : t('ui.soil.drain_well'),
    salt: ec == null ? null : salty ? t('ui.soil.salty', { n: ec.toFixed(1) }) : t('ui.soil.salt_low'),
    rotation,
    source: soilSourceName(s?.source?.id ?? s?.awc_mm_per_m?.source?.id),
  };
}
/** The soil map behind the soil facts, from the soil's source id. */
export function soilSourceName(id?: string | null) {
  const k = (id ?? '').toLowerCase();
  if (/aafc|slc/.test(k)) return t('ui.soil.src_aafc');
  if (/soilgrids|isric/.test(k)) return t('ui.soil.src_sg');
  if (/ssurgo|usda|nrcs/.test(k)) return t('ui.soil.src_ssurgo');
  return t('ui.soil.src_other');
}
/** Sand / silt / clay as one stacked bar with a key underneath. */
export function SoilBar({ mix }: { mix: { sand: number; silt: number; clay: number } }) {
  const tot = mix.sand + mix.silt + mix.clay || 1;
  const parts = (['sand', 'silt', 'clay'] as const).map((k) => ({ k, w: (mix[k] / tot) * 100, pct: Math.round(mix[k]) }));
  return (
    <span className="soilbar" data-testid="soil-bar">
      <span className="sb-track" role="img" aria-label={parts.map((x) => `${t(`ui.soil.${x.k}`)} ${x.pct}%`).join(', ')}>
        {parts.map((x) => <i key={x.k} style={{ width: `${x.w}%`, background: SOIL_COLOR[x.k] }} />)}
      </span>
      <span className="sb-key">{parts.map((x) => <span key={x.k}><i style={{ background: SOIL_COLOR[x.k] }} />{t(`ui.soil.${x.k}`).replace(/^./, (c) => c.toUpperCase())} {x.pct}%</span>)}</span>
    </span>
  );
}

/** One BC order in a few words, from its kind: an order to stop irrigating (with its licence count) or a rescission. */
export const orderText = (o: WaterOrder) => o.kind === 'rescission' ? t('ui.order.rescinded')
  : `${t('ui.order.stop')}${o.licences ? ` (${t('ui.order.licences', { n: o.licences })})` : ''}${o.effective && o.effective !== o.date ? `, ${t('ui.order.from', { date: fmtDate(o.effective) })}` : ''}`;
/** Water source, district, GSA and groundwater-basin status from the looked-up location (empty values left out). */
export function WaterLine({ loc }: { loc: Location }) {
  const w = loc.water;
  const wc = loc.water_context;
  if (loc.region === 'bc') {
    // BC: no water district or groundwater basin; the watershed and the Province's irrigation orders instead
    if (!wc) return <small className="na-line">{t('ui.water.nows')}</small>;
    return (
      <>{wc.watershed.split(';')[0]}.
        {wc.orders.map((o) => <span key={o.date + o.title} className="water-order"> {fmtDate(o.date)}: {orderText(o)}.{linkOf(o) && <> <a href={linkOf(o)!} target="_blank" rel="noreferrer">{t('ui.source')}</a></>}</span>)}
      </>
    );
  }
  const src = w?.source === 'surface' ? t('ui.water.surface') : w?.source === 'groundwater' ? t('ui.water.gw') : w?.source === 'mixed' ? t('ui.water.mixed') : null;
  if (!loc.water_real) return <>{src}<small className="na-line">{src ? '; ' : ''}{t('ui.water.nodistrict')}</small></>;
  const gsa = (Array.isArray(w.gsa) ? w.gsa : w.gsa ? [w.gsa] : []).filter(Boolean);
  const parts = [src, w.district, gsa.length ? `${t('ui.water.gsa')}: ${gsa.join(', ')}` : null].filter(Boolean);
  return (
    <>{parts.join('. ')}{parts.length ? '.' : ''}
      {w.sgma_status?.text && <span className="water-sgma"> {w.sgma_status.text}.</span>}
      {linkOf(w.sgma_status) && <> <a href={linkOf(w.sgma_status)!} target="_blank" rel="noreferrer">{t('ui.source')}</a></>}
    </>
  );
}

const CAUSE: Record<string, string> = { drought: t('ui.cause.drought'), excess_moisture: t('ui.cause.excess'), heat: t('ui.cause.heat'), other: t('ui.cause.other'), frost_other: t('ui.cause.other'), frost: t('ui.cause.frost'), cold: t('ui.cause.cold') };
const whenOf = (tt: number) => { const d = dekadOf(tt); return t('ui.when', { part: t(`ui.part.${d % 3}`), month: t(`ui.month.${Math.floor(d / 3) + 1}`) }); };
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
      {(mu || tex) && <div><dt>{t('ui.about.soil')}</dt><dd>{mu ? mu.split(',')[0] : ''}{tex ? `${mu ? ', ' : ''}${tex.toLowerCase()}` : ''} <cite><Src p={prov.soil} /></cite></dd></div>}
      {inFt != null && <div><dt>{t('ui.about.holds')}</dt><dd>{t('ui.about.holds_t', { n: inFt.toFixed(1) })}{inFt < 1.4 ? ` ${t('ui.about.holds_low')}` : inFt > 2 ? ` ${t('ui.about.holds_high')}` : ''}</dd></div>}
      {(dc || hg) && <div><dt>{t('ui.about.drainage')}</dt><dd>{dc}{hg ? `${dc ? '; ' : ''}${t('ui.about.runoff', { g: hg })}` : ''}</dd></div>}
      {s.ec_ds_per_m != null && <div><dt>{t('ui.about.salt')}</dt><dd className={saline ? 'warn' : ''}>{saline ? t('ui.about.salty') : t('ui.about.lowsalt')}<small> (EC {s.ec_ds_per_m.toFixed(1)} dS/m)</small></dd></div>}
      <div><dt>{loc.region === 'bc' ? t('ui.about.watershed') : t('ui.about.water')}</dt><dd><WaterLine loc={loc} /></dd></div>
      {dem?.slope_mean_pct != null && <div><dt>{t('ui.about.slope')}</dt><dd>{dem.slope_mean_pct < 2 ? t('ui.about.flat') : dem.slope_mean_pct < 5 ? t('ui.about.gentle') : t('ui.about.sloping')}, {t('ui.about.avg', { n: dem.slope_mean_pct.toFixed(1) })}{dem.low_spot_fraction ? `; ${t('ui.about.lowspots', { n: Math.round(dem.low_spot_fraction * 100) })}` : ''}. <cite>{t('ui.about.dem')} <Src p={prov.terrain} /></cite></dd></div>}
      {!rma && insGap && <div><dt>{t('ui.about.ins')}</dt><dd><GapLine gap={insGap} missing /></dd></div>}
      {rma && rma.total_usd == null && <div><dt>{t('ui.about.losses')}</dt><dd>{t('ui.about.causes')} {(rma.shares ?? []).map((x) => `${CAUSE[x.cause] ?? x.cause.replace(/_/g, ' ')} ${Math.round(x.share * 100)}%`).join(', ')}. {t('ui.about.nodollars')} <cite><Src p={prov.rma} /></cite>{insGap && <GapLine gap={insGap} missing={false} />}</dd></div>}
      {rma && rma.total_usd != null && <div><dt>{t('ui.about.ins')}</dt><dd>{t('ui.about.paid', { total: usd(rma.total_usd), scope: rma.scope, crop: rma.crop.replace('_forage', '').replace(/_/g, ' '), from: rma.from, to: rma.to, top: usd(rma.top_usd), year: rma.top_year })}{rma.share_drought >= 0.3 ? ` ${t('ui.about.drought_share', { n: Math.round(rma.share_drought * 100) })}` : ''} <cite>{t('ui.about.rma')} <Src p={prov.rma} /></cite>{insGap && <GapLine gap={insGap} missing={false} />}</dd></div>}
      <div><dt>{t('ui.about.bare')}</dt><dd>{ob && ob.years?.length ? <>{t('ui.about.bare_t', { n: ob.value, when })} <cite>{t('ui.about.seen', { from: ob.years[0], to: ob.years[ob.years.length - 1] })} {BARE_DEF} <Src p={prov.calendar} /></cite></> : loc.observed_cover.summary}</dd></div>
    </dl>
  );
}

export const CROP_COL = (c: string) => (c.startsWith('Rice') ? '#3d7fc4' : c === 'Left fallow' ? '#b08a5a' : c.startsWith('Alfalfa') || c.startsWith('Hay') ? '#4f8f3a' : c.startsWith('Corn') ? '#d4b23c' : c.startsWith('Wheat') ? '#c79a3a' : '#8a8a80');
export function CropRecord({ loc, prov, from = 2016 }: { loc: Location; prov: ProvMap; from?: number }) {
  const ys = years(loc).filter((y) => y >= from);
  const crops = [...new Set(ys.map((y) => cropKey(loc.crop_history[y])))];
  return (
    <div className="record">
      <div className="rec-row">
        {ys.map((y) => { const c = cropName(loc.crop_history[y]); return <span key={y} title={`${y}: ${c}`}><i style={{ background: CROP_COL(cropKey(loc.crop_history[y])) }} /><em>{y}</em></span>; })}
      </div>
      <div className="rec-key">{crops.map((c) => <span key={c}><i style={{ background: CROP_COL(c) }} />{cropName(c)}</span>)}</div>
      <cite>{cropMapName(loc)} · <Src p={prov.crop_history} /></cite>
    </div>
  );
}

export function EventLog({ events, setT }: { events: FieldEvent[]; setT: (t: number) => void }) {
  return (
    <div className="evlog">
      {events.map((e) => (
        <button key={e.date} onClick={() => setT(dateToT(e.date))} title={t('ui.ev.move')}>
          <time>{fmtDate(e.date)}</time>
          <span><b>{e.title}</b>{e.detail && <small>{e.detail}</small>}</span>
          {linkOf(e) && <a href={linkOf(e)!} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} title={t('ui.source')}><Icon name="link" size={13} /></a>}
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

export const yearLabel = (tt: number) => t('ui.when_year', { when: whenOf(tt), year: yearOf(tt) });

/** Honest line on how the water model compares with OpenET measured water use on this field (baseline crop years only). */
export function openetText(strategies: RotationStrategy[] | null | undefined) {
  const b = strategies?.find((s) => s.is_baseline), v = b?.water.etc_vs_openet_pct?.value;
  if (v == null) return t('ui.openet.none');
  const r = Math.round(Math.abs(v));
  return t(v >= 0 ? 'ui.openet.high' : 'ui.openet.low', { n: r });
}

/** The pick-list line, from the crop record: "Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022." */
export function recordLine(l: Location) {
  const ys = years(l).slice(-10), main = mainCrop(l);
  const n = ys.filter((y) => cropKey(l.crop_history[y]).startsWith(main.split(',')[0])).length;
  const fallow = ys.filter((y) => cropKey(l.crop_history[y]) === 'Left fallow');
  const list = (a: number[]) => (a.length > 1 ? `${a.slice(0, -1).join(', ')} ${t('ui.and')} ${a[a.length - 1]}` : String(a[0]));
  return `${t('ui.rec.in', { crop: tx(main.split(',')[0]), n, total: ys.length })}${fallow.length ? `; ${t('ui.rec.fallow', { list: list(fallow) })}` : ''}.`;
}
/** A rotation's name in a sentence: "rice + winter flood" (no "(current)", lower case). */
export const rotName = (s: { short_name: string }) => s.short_name.replace(/\s*\(current\)$/i, '').replace(/^\w/, (c) => c.toLowerCase());
/** Water need against what the grower can get, compared at the one decimal the app shows (5.24 vs 5.2 is "about even", never "0.0 short"). */
export function waterGap(need: number, have: number) {
  const tenths = Math.round(need * 10) - Math.round(have * 10);
  return { short: tenths > 0, even: tenths === 0, by: (Math.abs(tenths) / 10).toFixed(1) };
}
