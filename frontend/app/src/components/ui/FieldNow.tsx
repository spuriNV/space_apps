// "Your field now": plain answers in grower units for the timeline date (today by default).
// Each answer: a plain sentence first, then the number with its unit, then one small source line.
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import type { NasaNow, ProvMap, RegionalLive } from '../../api';
import { TODAY_T } from '../../lib';
import type { Daily } from '../../season';
import { HOT_F, cropWaterSoFar, fmtIn, fmtShort, heatFrost, rainSoFar, type RainSoFar } from '../../season';
import { MONTHS, atT, latestAt, dataT, dekadOf, fieldState, lastDataT, mmToAfac, ordinal, yearOf } from '../../lib';
import { Src, calSource, cropName, openetText } from './shared';
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

/** Rain so far this season: today from GET .../nasa_now (NASA GPM IMERG, normal 2001-2025), other dates from the daily record. */
export function rainNow(nasaNow: NasaNow | null, daily: Daily | null, t: number): RainSoFar | null {
  const nn = t === TODAY_T && nasaNow?.rainWyMm != null && nasaNow.rainWyNormalMm ? nasaNow : null;
  if (nn) return { period: { label: `1 Oct to ${fmtShort(nn.rainDate!).replace(/ \d{4}$/, '')}`, from: '', to: '', current: true }, inches: nn.rainWyMm! / 25.4, normal: nn.rainWyNormalMm! / 25.4, nSeasons: 25, pct: (nn.rainWyMm! / nn.rainWyNormalMm!) * 100, source: 'imerg' };
  return daily ? rainSoFar(daily, t) : null;
}
export interface FieldNowProps { nasaNow: NasaNow | null; loc: Location; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; t: number; daily: Daily | null; prov: ProvMap }
export function FieldNow(p: FieldNowProps) {
  const { loc, cal, t } = p;
  const dt = cal ? dataT(cal, t) : t, behind = cal ? t > lastDataT(cal) : false;
  const fs = cal ? fieldState(cal, dt, 'rule') : null;
  const st = cal ? stage(cal, dt) : null;
  const yr = yearOf(t), crop = loc.crop_history[yr];
  const lastRec = Math.max(...Object.keys(loc.crop_history).map(Number));
  const base = p.strategies?.find((s) => s.is_baseline);
  const need = base ? base.water.irrigation_need_mm : null;
  const rain = rainNow(p.nasaNow, p.daily, t);
  const hf = p.daily ? heatFrost(p.daily, t) : null;
  const cw = p.daily && base ? cropWaterSoFar(p.daily, base, t) : null;
  const sm = p.regional ? latestAt(p.regional.smap_rootzone_pct.values, t) : null, smap = sm?.v ?? null;
  const gr = p.regional ? latestAt(p.regional.grace_gw_pct.values, t) : null, grace = gr?.v ?? null;
  const behindNote = behind ? ` Latest clear view ${whenT(dt)}${yearOf(dt) < yr ? `; ${yr} imagery not processed yet` : ''}.` : '';
  return (
    <dl className="answers">
      <div className="ans">
        <dt>What is growing, and how far along?</dt>
        <dd>
          <b><i className={`sw-${st?.sw ?? 'none'}`} />{st?.text ?? 'Loading…'}</b>
          <span>{crop ? `${cropName(crop)} on record for ${yr}.` : `${yr} crop map not published yet (USDA, early ${yr + 1}). ${lastRec}: ${cropName(loc.crop_history[lastRec]).toLowerCase()}.`} {st?.sub}</span>
          <cite>{calSource(p.prov.calendar)}, 100 ft squares; crop from the USDA Cropland Data Layer.{behindNote} <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>How much green cover is there? <What k="greenness" /></dt>
        <dd>
          {fs && fs.cls !== 'u' && fs.cls !== 'w' ? <>
            <b>{fs.ndvi >= 0.6 ? 'Full green canopy' : fs.ndvi >= 0.35 ? 'Partly green' : fs.ndvi >= 0.2 ? 'Thin green cover' : 'Little or no green cover'}</b>
            <span>Greenness {fs.ndvi.toFixed(2)} on a 0 to 1 scale; above 0.6 is a full canopy.</span>
          </> : <b>{fs?.cls === 'w' ? 'Under water, so no green reading' : 'No reading for this date'}</b>}
          <cite>Greenness from {calSource(p.prov.calendar).replace(' satellites', '')}, field average, {whenT(dt)}. <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>How much rain so far this season?</dt>
        <dd>
          {rain ? <>
            <b>{rain.period.current ? '' : 'No readings for this winter yet. '}{rain.pct != null ? `${rain.period.current ? 'So far' : 'Last season was'} ${vsNormal(rain.pct, 'wetter than normal', 'drier than normal')}` : ''}</b>
            <span>{fmtIn(rain.inches)} inches {rain.period.label}; normal is {rain.normal != null ? `${fmtIn(rain.normal)} inches` : 'not known'}{rain.pct != null ? ` (${Math.round(rain.pct)}% of normal)` : ''}.</span>
            <cite>{rain.source === 'imerg' ? 'NASA GPM IMERG satellite rain over the field (one reading for a 6-mile square)' : 'NOAA weather stations near the field, averaged'}; normal = the same dates in the {rain.nSeasons} seasons before. <Src p={p.prov.daily} /></cite>
          </> : <b>Loading…</b>}
        </dd>
      </div>
      <div className="ans">
        <dt>How much water has the crop used? <What k="et" /></dt>
        <dd>
          {cw ? <>
            <b>{cw.period.current ? 'So far this year' : 'Last year'}: {vsNormal(cw.pct, 'more than normal', 'less than normal')}</b>
            <span>About {fmtIn(cw.inches)} in of water {cw.period.label}; normal is {fmtIn(cw.normal)} in. That is {mmToAfac(cw.inches * 25.4).toFixed(1)} acre-feet per acre.{base?.water.openet_et_mm_season ? ` Measured on this field (OpenET), a full year averages about ${fmtIn(base.water.openet_et_mm_season.value / 25.4)} in.` : ''}</span>
            <cite>NASA POWER weather (sun, wind, humidity) drives the rotation model for today’s rotation. {openetText(p.strategies)} <Src p={p.prov.strategies} /></cite>
          </> : <b>{base ? 'Loading…' : 'No rotation model for this field'}</b>}
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
          <b>{smap == null ? 'No soil reading' : band(smap, 'Soil wetter than usual', 'Soil about normal', 'Soil drier than usual')}; {grace == null ? 'no groundwater reading' : band(grace, 'more groundwater than usual', 'groundwater about normal', 'less groundwater than usual').toLowerCase()}</b>
          <span>{smap != null && `Soil moisture ${ordinal(Math.round(smap))} percentile for the date${sm && sm.t < t - 1 ? ` (latest, ${whenT(sm.t)})` : ''}; 50 is normal. `}{grace != null && `Groundwater ${ordinal(Math.round(grace))} percentile${gr && gr.t < t - 1 ? ` (latest, ${whenT(gr.t)})` : ''}, whole basin, not your own well.`}</span>
          <cite>{p.regionalLive.soilSource === 'grace_da' ? 'Soil: NASA GRACE-FO with a land model, root zone, one reading for a 17-mile square (NASA SMAP readings still downloading).' : `Soil: NASA SMAP satellite, one reading for a 6-mile square${p.regionalLive.smap ? '' : ' (example numbers)'}.`} Groundwater: NASA GRACE-FO satellites{p.regionalLive.grace ? '' : ' (example numbers)'}, weekly. <Src p={p.prov.regional} /></cite>
        </dd>
      </div>
      <div className="ans">
        <dt>How many hot days and frost nights? <What k="frost" /></dt>
        <dd>
          {hf ? <>
            <b>{hf.hot} day{hf.hot === 1 ? '' : 's'} at or above {HOT_F} °F {hf.period.current ? 'so far this year' : `in ${hf.period.label.replace('last year, ', '')}`}</b>
            <span>Normal for the same dates: {hf.hotNormal != null ? Math.round(hf.hotNormal) : '?'}. Frost nights (32 °F or lower), {hf.frostPeriod.label}: {hf.frost}; normal {hf.frostNormal != null ? Math.round(hf.frostNormal) : '?'}.</span>
            <cite>NOAA weather stations near the field. NASA POWER is not used for heat here: it runs about 6 °F hot in summer against the stations. <Src p={p.prov.daily} /></cite>
          </> : <b>Loading…</b>}
        </dd>
      </div>
    </dl>
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
