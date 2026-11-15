// "Your field now": plain answers in grower units for the timeline date (today by default).
// Each answer: a plain sentence first, then the number with its unit, then one small source line.
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import type { Extras, NasaNow, ProvMap, RegionalLive } from '../../api';
import { TODAY_T } from '../../lib';
import type { Daily } from '../../season';
import { HOT_F, cropWaterSoFar, fmtIn, fmtShort, heatFrost, rainSoFar, type RainSoFar } from '../../season';
import { MONTHS, atT, latestAt, dataT, dekadOf, fieldState, lastDataT, mmToAfac, ordinal, yearOf } from '../../lib';
import { SoilBar, Src, calSource, cropName, openetText, soilFacts } from './shared';
import { What } from './What';

const PART = ['early', 'mid', 'late'];
const dk = (d: number) => `${PART[d % 3]} ${MONTHS[Math.floor(d / 3)]}`;
export const whenT = (t: number) => `${dk(dekadOf(t))} ${yearOf(t)}`;
const band = (pct: number, hi: string, mid: string, lo: string) => (pct >= 67 ? hi : pct > 33 ? mid : lo);
const vsNormal = (pct: number | null, wet: string, dry: string) => (pct == null ? '' : pct >= 115 ? wet : pct <= 85 ? dry : 'about normal');

function stage(cal: Calendar, t: number) {
  const y = cal.years[Math.floor(t / 36)], d = t % 36, c = y.rule[d];
  const up = y.greenup_dekad, dn = y.senescence_dekad;
  if (c === 'w') return { sw: 'water', text: 'Under water', sub: d >= 30 || d <= 5 ? 'Flooded for the winter, as most years.' : 'Standing water on the field.' };
  if (c === 'c') return { sw: 'good', text: up != null && d >= up && (dn == null || d < dn) ? `Crop growing, green since ${dk(up)}` : 'Crop growing, full green cover', sub: '' };
  if (c === 'p') return { sw: 'part', text: 'Thin cover', sub: 'Some green, less than a full crop: a young crop, regrowth after a cutting, stubble or weeds.' };
  if (c === 'b') return { sw: 'bare', text: dn != null && d > dn ? `Bare since harvest in ${dk(dn)}` : 'Bare ground', sub: '' };
  return { sw: 'none', text: 'No clear satellite view', sub: 'Clouds, or no image within 30 days.' };
}

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/** OpenET measured crop water use from 1 Jan to the timeline month; the latest year with those months if this year is not out yet. */
export function measuredSoFar(oet: Extras['openet'], modelMonths: number[] | null, t: number) {
  if (!oet?.length) return null;
  const y = yearOf(t), m = Math.floor(dekadOf(t) / 3) + 1;
  const sum = (yy: number) => { const rows = oet.filter((r) => +r.month.slice(0, 4) === yy && +r.month.slice(5, 7) <= m); return rows.length === m ? rows.reduce((a, r) => a + r.in, 0) : null; };
  let yy = y, v = sum(y);
  while (v == null && yy > y - 3) { yy--; v = sum(yy); }
  if (v == null) return null;
  const model = (modelMonths ?? []).slice(0, m).reduce((a, x) => a + x, 0) / 25.4;
  return { inches: v, model, current: yy === y, label: `Jan–${MON[m - 1]} ${yy}` };
}
/** One sentence on crop-stress weeks for the season of the timeline date (or the latest season with checks). */
export function stressLine(ex: Extras, t: number) {
  const s = ex.stress;
  if (!s) return 'Crop-stress check not loaded';
  const years = Object.keys(s.evaluated).map(Number).filter((y) => y <= yearOf(t)).sort();
  const y = years[years.length - 1];
  if (y == null) return 'No growing season checked yet';
  const wk = s.weeks.filter((w) => w.start.startsWith(String(y)));
  if (!wk.length) return `No crop-stress weeks in the ${y} season`;
  const why: Record<string, number> = {};
  wk.forEach((w) => w.drivers.forEach((d) => (why[d] = (why[d] ?? 0) + 1)));
  const top = Object.entries(why).sort((a, b) => b[1] - a[1])[0]?.[0];
  return `${wk.length} crop-stress week${wk.length === 1 ? '' : 's'} in the ${y} season${top ? `, mostly ${DRIVER[top] ?? 'unusual weather'}` : ''}`;
}
export const DRIVER: Record<string, string> = { z_tmax: 'unusual heat', z_eto: 'very thirsty air', z_ndvi: 'weaker growth than in its other years', iforest: 'an unusual mix of heat, dryness and growth' };
/** One sentence on standing water: the latest clear OPERA view up to the timeline date, plus the winter record. */
export function waterLine(ex: Extras, t: number) {
  const w = ex.water;
  if (!w) return 'Standing-water record not loaded.';
  const cut = `${yearOf(t)}-${String(Math.floor(dekadOf(t) / 3) + 1).padStart(2, '0')}-31`;
  const last = [...w.scenes].filter((s) => s.date <= cut).pop();
  const wet = w.seasons.filter((s) => s.seen).length, n = w.seasons.filter((s) => s.clear >= 5).length;
  const rec = n ? ` More than half the field was under water in ${wet} of ${n} winters with clear views.` : '';
  return last ? `NASA OPERA last saw the field clearly on ${fmtShort(last.date)}: ${last.frac >= 0.5 ? `${Math.round(last.frac * 100)}% under water` : last.frac >= 0.1 ? `water on ${Math.round(last.frac * 100)}% of it` : 'no standing water'}.${rec}` : `No clear OPERA view yet.${rec}`;
}

/** Rain so far this season: today from GET .../nasa_now (NASA GPM IMERG, normal 2001-2025), other dates from the daily record. */
export function rainNow(nasaNow: NasaNow | null, daily: Daily | null, t: number): RainSoFar | null {
  const nn = t === TODAY_T && nasaNow?.rainWyMm != null && nasaNow.rainWyNormalMm ? nasaNow : null;
  if (nn) return { period: { label: `1 Oct to ${fmtShort(nn.rainDate!).replace(/ \d{4}$/, '')}`, from: '', to: '', current: true }, inches: nn.rainWyMm! / 25.4, normal: nn.rainWyNormalMm! / 25.4, nSeasons: 25, pct: (nn.rainWyMm! / nn.rainWyNormalMm!) * 100, source: 'imerg' };
  return daily ? rainSoFar(daily, t) : null;
}
export type LoadState = 'loading' | 'ready' | 'timeout';
/** Thin loading line for one answer. */
const Skel = () => <span className="skel" aria-label="Loading" />;
/** The latest 10-day step with a clear satellite reading at or before t, at most 6 weeks back. */
function latestClearT(cal: Calendar, t: number, maxBack = 4): number | null {
  for (let k = t; k >= 0 && t - k <= maxBack; k--) { const y = cal.years[Math.floor(k / 36)]; const c = y?.rule[k % 36]; if (c && c !== 'u') return k; }
  return null;
}
/** One small reading: label, value, a bar with a reference mark. */
function Meter(m: { label: string; value: string | null; state: LoadState; pct: number | null; mark: number | null; markLabel: string; note: string; warn?: boolean }) {
  return (
    <div className="meter">
      <span className="m-label">{m.label}</span>
      {m.value == null ? (m.state === 'timeout' ? <span className="m-val na">Not available</span> : <span className="skel" />) : <>
        <span className="m-val">{m.value}</span>
        <i className="m-track">{m.pct != null && <em className={`m-fill ${m.warn ? 'warn' : ''}`} style={{ width: `${m.pct * 100}%` }} />}{m.mark != null && <b className="m-mark" style={{ left: `${Math.min(1, m.mark) * 100}%` }} title={m.markLabel} />}</i>
        <span className="m-note">{m.note}{m.mark != null ? ` · line = ${m.markLabel}` : ''}</span>
      </>}
    </div>
  );
}
export interface FieldNowProps { dataState: LoadState; dailyState: LoadState; thumb: { bbox: number[] } | null; extras: Extras; nasaNow: NasaNow | null; loc: Location; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; t: number; daily: Daily | null; prov: ProvMap; mode?: 'all' | 'takeaway' | 'glance' }
export function FieldNow(p: FieldNowProps) {
  const { loc, cal, t } = p;
  const dt = cal ? latestClearT(cal, t) ?? dataT(cal, t) : t, behind = cal ? t > lastDataT(cal) : false;
  const ago = t - dt, agoText = ago <= 0 ? '' : ago === 1 ? ', about 10 days ago' : `, about ${Math.round((ago * 10) / 7)} weeks ago`;
  const pend = (s: LoadState) => (s === 'timeout' ? <b className="na">Not available right now</b> : <Skel />);
  const fs = cal ? fieldState(cal, dt, 'rule') : null;
  const st = cal ? stage(cal, dt) : null;
  const yr = yearOf(t), crop = loc.crop_history[yr];
  const lastRec = Math.max(...Object.keys(loc.crop_history).map(Number));
  const base = p.strategies?.find((s) => s.is_baseline);
  const need = base ? base.water.irrigation_need_mm : null;
  const rain = rainNow(p.nasaNow, p.daily, t);
  const ms = measuredSoFar(p.extras.openet, base?.water.etc_by_month_mm ?? null, t);
  const hf = p.daily ? heatFrost(p.daily, t) : null;
  const cw = p.daily && base ? cropWaterSoFar(p.daily, base, t) : null;
  const sm = p.regional ? latestAt(p.regional.smap_rootzone_pct.values, t) : null, smap = sm?.v ?? null;
  const gr = p.regional ? latestAt(p.regional.grace_gw_pct.values, t) : null, grace = gr?.v ?? null;
  const behindNote = dt < t ? ` Latest clear view ${whenT(dt)}${agoText}${yearOf(dt) < yr ? `; ${yr} imagery not processed yet` : ''}.` : '';
  const limit = p.allocation ?? null, needAf = need ? mmToAfac(need.value) : null;
  const y26 = cal?.years.find((y) => y.year === yr);
  const waterFit = needAf == null || limit == null ? null : needAf > limit ? `short by about ${(needAf - limit).toFixed(1)} acre-ft/acre` : 'fits your water limit';
  const soilWords = smap == null ? null : band(smap, 'Soil wetter than usual', 'Soil about normal', 'Soil drier than usual');
  const soil = soilFacts(loc.soil);
  const short = needAf != null && limit != null && needAf > limit;
  const takeaway = waterFit
    ? (short ? `No. Short by about ${(needAf! - limit!).toFixed(1)} acre-ft/acre` : 'Yes. It fits your water limit')
    : soilWords ?? (st ? st.text : null);
  const takeawaySub = waterFit
    ? `Today’s rotation needs about ${needAf!.toFixed(1)} acre-ft/acre a year; your limit is ${limit!.toFixed(1)}${p.exampleLimit ? ' (an example, set yours in step 4)' : ''}.${soilWords ? ` ${soilWords}.` : ''}`
    : null;
  const mode = p.mode ?? 'all';
  const showTake = mode === 'all' || mode === 'takeaway';
  const showGlance = mode === 'all' || mode === 'glance';
  return (
    <>
    {showTake && (takeaway
      ? <div className={`now-take ${short ? 'short' : ''}`} data-testid="now-takeaway"><b>{takeaway}.</b>{takeawaySub && <span>{takeawaySub}</span>}</div>
      : <div className="now-take"><Skel /></div>)}
    {showTake && (soil.mix || soil.texture || soil.holds) && (
      <div className="soil-card" data-testid="soil-answer">
        <p className="soil-q">What is the soil like?</p>
        {soil.texture && <b className="soil-tex">{soil.texture}</b>}
        {soil.mix && <SoilBar mix={soil.mix} />}
        <p className="soil-facts">{[soil.holds, soil.drains, soil.salt].filter(Boolean).join(' ')}</p>
        {soil.rotation && <p className="soil-rot">{soil.rotation}</p>}
        <cite>{soil.source}. <Src p={p.prov.soil} /></cite>
      </div>
    )}
    {showGlance && <div className="glance" data-testid="glance">
      <div className="gl-top">
        <span className="gl-thumb">
          <img src={`${import.meta.env.BASE_URL}thumbs/${loc.id}.jpg`} alt="" />
          {p.thumb && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={loc.geometry.coordinates[0].map(([x, y]) => `${(((x - p.thumb!.bbox[0]) / (p.thumb!.bbox[2] - p.thumb!.bbox[0])) * 360).toFixed(1)},${(((p.thumb!.bbox[3] - y) / (p.thumb!.bbox[3] - p.thumb!.bbox[1])) * 240).toFixed(1)}`).join(' ')} /></svg>}
        </span>
        <span className="gl-season">
          <small>{yr} so far</small>
          <span className="gl-strip">
            {(y26?.rule ?? 'u'.repeat(36)).split('').map((c, k) => <em key={k} className={`c-${c}`} />)}
            <i className="gl-today" style={{ left: `${((dekadOf(t) + 0.5) / 36) * 100}%` }} title={whenT(t)} />
          </span>
          <span className="gl-months"><span>Jan</span><span>Apr</span><span>Jul</span><span>Oct</span></span>
          <b>{st ? st.text : '…'}</b>
        </span>
      </div>
      <div className="gl-grid gl-core">
        <Meter label="Water need vs limit" value={needAf != null ? `${needAf.toFixed(1)} acre-ft/acre` : null} state={p.dataState} pct={needAf != null && limit ? Math.min(1, needAf / (Math.max(needAf, limit) * 1.2)) : null} mark={needAf != null && limit ? limit / (Math.max(needAf, limit) * 1.2) : null} markLabel="your limit" warn={needAf != null && limit != null && needAf > limit} note={limit != null ? (needAf != null && needAf > limit ? `Over the ${limit.toFixed(1)} limit` : `Within the ${limit.toFixed(1)} limit`) + (p.exampleLimit ? ' (example)' : '') : ''} />
        <Meter label="Rain since 1 Oct" value={rain ? `${fmtIn(rain.inches)} in` : null} state={p.dailyState} pct={rain && rain.normal ? Math.min(1, rain.inches / (Math.max(rain.inches, rain.normal) * 1.25)) : null} mark={rain && rain.normal ? rain.normal / (Math.max(rain.inches, rain.normal) * 1.25) : null} markLabel="normal" note={rain?.pct != null ? (rain.pct >= 115 ? 'Wetter than normal' : rain.pct <= 85 ? 'Drier than normal' : 'About normal') : ''} />
        <div className="meter">
          <span className="m-label">Soil moisture</span>
          {!p.regional ? (p.dataState === 'timeout' ? <span className="m-val na">Not available</span> : <span className="skel" />) : <>
            <span className="m-val">{soilWords ?? 'No reading'}</span>
            <span className="m-dots">
              <i className="m-track"><em className="m-mid" />{smap != null && <b className="dot soil" style={{ left: `${smap}%` }} title={`Soil moisture ${ordinal(Math.round(smap))} percentile`} />}{grace != null && <b className="dot gw" style={{ left: `${grace}%` }} title={`Groundwater ${ordinal(Math.round(grace))} percentile`} />}</i>
            </span>
            <span className="m-note"><i className="k soil" />soil <i className="k gw" />groundwater · middle = normal</span>
          </>}
        </div>
        <Meter label="Greenness" value={fs && fs.cls !== 'u' && fs.cls !== 'w' ? (fs.ndvi >= 0.6 ? 'Full canopy' : fs.ndvi >= 0.35 ? 'Partly green' : 'Thin cover') : null} state={p.dataState} pct={fs && fs.cls !== 'u' && fs.cls !== 'w' ? Math.max(0, Math.min(1, fs.ndvi)) : null} mark={0.6} markLabel="full canopy" note={fs && fs.cls !== 'u' && fs.cls !== 'w' ? 'From the satellite view' : fs?.cls === 'w' ? 'Under water' : ''} />
      </div>
    </div>}
    {mode === 'all' && <dl className="answers d-only">
      <div className="ans">
        <dt>What is growing, and how far along?</dt>
        <dd>
          {st ? <b><i className={`sw-${st.sw}`} />{st.text}</b> : pend(p.dataState)}
          <span>{crop ? `${cropName(crop)} on record for ${yr}.` : `${yr} crop map not published yet (AAFC, early ${yr + 1}). ${lastRec}: ${cropName(loc.crop_history[lastRec]).toLowerCase()}.`} {st?.sub}</span>
          <cite>{calSource(p.prov.calendar)}, 100 ft squares; crop from the AAFC Annual Crop Inventory.{behindNote} <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>How much green cover is there? <What k="greenness" /></dt>
        <dd>
          {fs && fs.cls !== 'u' && fs.cls !== 'w' ? <>
            <b>{fs.ndvi >= 0.6 ? 'Full green canopy' : fs.ndvi >= 0.35 ? 'Partly green' : fs.ndvi >= 0.2 ? 'Thin green cover' : 'Little or no green cover'}</b>
            <span>Greenness {fs.ndvi.toFixed(2)} on a 0 to 1 scale; above 0.6 is a full canopy.</span>
          </> : !cal ? pend(p.dataState) : <b>{fs?.cls === 'w' ? 'Under water, so no green reading' : 'No clear view in the last 6 weeks'}</b>}
          <cite>Greenness from {calSource(p.prov.calendar).replace(' satellites', '')}, field average, {whenT(dt)}{agoText}. <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>How much rain so far this season?</dt>
        <dd>
          {rain ? <>
            <b>{rain.period.current ? '' : 'No readings for this winter yet. '}{rain.pct != null ? `${rain.period.current ? 'So far' : 'Last season was'} ${vsNormal(rain.pct, 'wetter than normal', 'drier than normal')}` : ''}</b>
            <span>{fmtIn(rain.inches)} inches {rain.period.label}; normal is {rain.normal != null ? `${fmtIn(rain.normal)} inches` : 'not known'}{rain.pct != null ? ` (${Math.round(rain.pct)}% of normal)` : ''}.</span>
            <cite>{rain.source === 'imerg' ? 'NASA GPM IMERG satellite rain over the field (one reading for a 6-mile square)' : 'NOAA weather stations near the field, averaged'}; normal = the same dates in the {rain.nSeasons} seasons before. <Src p={p.prov.daily} /></cite>
          </> : pend(p.dailyState)}
        </dd>
      </div>
      <div className="ans">
        <dt>How much water has the crop used? <What k="et" /></dt>
        <dd>
          {ms && ms.current ? <>
            <b>Measured so far this year: {fmtIn(ms.inches)} in</b>
            <span>{ms.label}, measured on this field. Our model for the same months: {fmtIn(ms.model)} in. That is {mmToAfac(ms.inches * 25.4).toFixed(1)} acre-feet per acre.</span>
            <cite>OpenET satellite measurement (ensemble of 6 models built on Landsat), monthly, this field’s outline. <Src p={p.prov.openet} /></cite>
          </> : cw ? <>
            <b>{cw.period.current ? 'So far this year' : 'Last year'}: {vsNormal(cw.pct, 'more than normal', 'less than normal')}</b>
            <span>About {fmtIn(cw.inches)} in of water {cw.period.label}, estimated; normal is {fmtIn(cw.normal)} in. That is {mmToAfac(cw.inches * 25.4).toFixed(1)} acre-feet per acre.{ms ? ` Measured on this field by OpenET for ${ms.label}: ${fmtIn(ms.inches)} in (our model for those months: ${fmtIn(ms.model)} in).` : ''}</span>
            <cite>Estimate: rotation model driven by NASA POWER sun, wind and humidity{ms ? '; measured: OpenET satellite data, which ends a few months behind' : ''}. {openetText(p.strategies, p.loc)} <Src p={p.prov.strategies} /></cite>
          </> : !p.strategies || !p.daily ? pend(p.daily ? p.dataState : p.dailyState) : <b>No rotation model for this field</b>}
        </dd>
      </div>
      {need && (
        <div className="ans">
          <dt>Will the water limit cover irrigation? <What k="waterBalance" /></dt>
          <dd>
            <b>{p.allocation == null ? `About ${mmToAfac(need.value).toFixed(1)} acre-feet per acre a year` : mmToAfac(need.value) > p.allocation ? `Short by about ${(mmToAfac(need.value) - p.allocation).toFixed(1)} acre-feet per acre` : 'Fits your limit in a typical year'}</b>
            <span>Today’s rotation needs about {mmToAfac(need.value).toFixed(1)} acre-feet per acre a year (likely {mmToAfac(need.low ?? need.value).toFixed(1)}–{mmToAfac(need.high ?? need.value).toFixed(1)}){p.allocation != null ? `; the limit is ${p.allocation.toFixed(1)}` : ''}.{p.exampleLimit && <em className="ex-limit"> {p.allocation?.toFixed(1)} is an example limit, change to yours on Compare.</em>}</span>
            <cite>Rotation model with NASA POWER weather: crop water use minus rain, typical year 2015–2025. <Src p={p.prov.strategies} /></cite>
          </dd>
        </div>
      )}
      <div className="ans">
        <dt>Is the soil wetter or drier than usual? And the groundwater? <What k="soilAnomaly" /></dt>
        <dd>
          {!p.regional ? pend(p.dataState) : <b>{smap == null ? 'No soil reading' : band(smap, 'Soil wetter than usual', 'Soil about normal', 'Soil drier than usual')}; {grace == null ? 'no groundwater reading' : band(grace, 'more groundwater than usual', 'groundwater about normal', 'less groundwater than usual').toLowerCase()}</b>}
          <span className="d-only">{smap != null && `Soil moisture ${ordinal(Math.round(smap))} percentile for the date${sm && sm.t < t - 1 ? ` (latest, ${whenT(sm.t)})` : ''}; 50 is normal. `}{grace != null && `Groundwater ${ordinal(Math.round(grace))} percentile${gr && gr.t < t - 1 ? ` (latest, ${whenT(gr.t)})` : ''}, whole basin, not your own well.`}</span>
          <cite>{p.regionalLive.soilSource === 'grace_da' ? 'Soil: NASA GRACE-FO with a land model, root zone, one reading for a 17-mile square (NASA SMAP readings still downloading).' : `Soil: NASA SMAP satellite, one reading for a 6-mile square${p.regionalLive.smap ? '' : ' (example numbers)'}.`} Groundwater: NASA GRACE-FO satellites{p.regionalLive.grace ? '' : ' (example numbers)'}, weekly. <Src p={p.prov.regional} /></cite>
        </dd>
      </div>
      <div className="ans d-only">
        <dt>Has the crop been stressed, or the field under water? <What k="stress" /></dt>
        <dd>
          {p.dataState !== 'ready' ? pend(p.dataState) : <><b>{stressLine(p.extras, t)}</b>
          <span>{waterLine(p.extras, t)}</span></>}
          <cite>Crop stress: two statistical methods on satellite greenness and NASA POWER heat and dryness, growing season only. Standing water: NASA OPERA, 100 ft squares, clear images only. <Src p={p.prov.stress ?? p.prov.water_seen} /></cite>
        </dd>
      </div>
      <div className="ans d-only">
        <dt>How many hot days and frost nights? <What k="frost" /></dt>
        <dd>
          {hf ? <>
            <b>{hf.hot} day{hf.hot === 1 ? '' : 's'} at or above {HOT_F} °F {hf.period.current ? 'so far this year' : `in ${hf.period.label.replace('last year, ', '')}`}</b>
            <span>Normal for the same dates: {hf.hotNormal != null ? Math.round(hf.hotNormal) : '?'}. Frost nights (32 °F or lower), {hf.frostPeriod.label}: {hf.frost}; normal {hf.frostNormal != null ? Math.round(hf.frostNormal) : '?'}.</span>
            <cite>NOAA weather stations near the field. NASA POWER is not used for heat here: it runs about 6 °F hot in summer against the stations. <Src p={p.prov.daily} /></cite>
          </> : pend(p.dailyState)}
        </dd>
      </div>
    </dl>}
    </>
  );
}

/** What happened on this field in the last 3 seasons, one line each. */
export function LastSeasons({ loc, cal, t }: { loc: Location; cal: Calendar | null; t: number }) {
  if (!cal) return null;
  const last = yearOf(lastDataT(cal));
  const ys = cal.years.filter((y) => y.year <= last && y.year > last - 3).reverse();
  return (
    <ul className="seasons">
      {ys.map((y) => {
        const n = (c: string) => y.rule.split('').filter((x) => x === c).length * 10;
        const cr = cropName(loc.crop_history[y.year]);
        return (
          <li key={y.year}>
            <b>{y.year}</b>
            <span>{cr}. Green about {n('c')} days, thin {n('p')}, bare {n('b')}, flooded {n('w')}{n('u') ? `, no clear view ${n('u')}` : ''}.</span>
            <i className="mini-strip">{y.rule.split('').map((c, i) => <em key={i} className={`c-${c}`} />)}</i>
          </li>
        );
      })}
      {yearOf(t) > last && <li className="dim"><b>{yearOf(t)}</b><span>Not processed yet: satellite imagery and the crop map for {yearOf(t)} are still to come.</span></li>}
    </ul>
  );
}
