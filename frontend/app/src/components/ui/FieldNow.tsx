// "Your field now": plain answers in grower units for the timeline date (today by default).
// Each answer: a plain sentence first, then the number with its unit, then one small source line.
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import { bcGap, isBC, type Extras, type NasaNow, type ProvMap, type RegionalLive } from '../../api';
import { TODAY_T } from '../../lib';
import type { Daily } from '../../season';
import { HOT_F, cropWaterSoFar, fmtIn, fmtShort, heatFrost, rainSoFar, type RainSoFar } from '../../season';
import { MONTHS, atT, latestAt, dataT, dekadOf, fieldState, isRainFed, lastDataT, mmToAfac, ordinal, RAIN_FED, yearOf } from '../../lib';
import { GapLine, SoilBar, Src, calSourceShort, cropMapName, cropKey, cropName, openetText, soilFacts, stationsName } from './shared';
import { What } from './What';
import { CountUp } from './motion';
import { ThisWeek } from '../week/ThisWeek';
import { t as tr, isEs } from '../../i18n';

const dk = (d: number) => tr('ui.when', { part: tr(`ui.part.${d % 3}`), month: MONTHS[Math.floor(d / 3)] });
export const whenT = (t: number) => tr('ui.when_year', { when: dk(dekadOf(t)), year: yearOf(t) });
/** "50th" in English; the bare number in Spanish ("percentil 50"). */
const ord = (n: number) => (isEs ? String(n) : ordinal(n));
const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
const band = (pct: number, hi: string, mid: string, lo: string) => (pct >= 67 ? hi : pct > 33 ? mid : lo);
const vsNormal = (pct: number | null, wet: string, dry: string) => (pct == null ? '' : pct >= 115 ? wet : pct <= 85 ? dry : tr('ui.fn2.aboutnormal'));

export function stage(cal: Calendar, t: number) {
  const y = cal?.years?.[Math.floor(t / 36)], d = t % 36, c = y?.rule?.[d];
  const up = y?.greenup_dekad ?? null, dn = y?.senescence_dekad ?? null;
  if (c === 'w') return { sw: 'water', text: tr('ui.st.water'), sub: d >= 30 || d <= 5 ? tr('ui.st.flooded') : tr('ui.st.standing') };
  if (c === 'c') return { sw: 'good', text: up != null && d >= up && (dn == null || d < dn) ? tr('ui.st.growing_since', { when: dk(up) }) : tr('ui.st.growing'), sub: '' };
  if (c === 'p') return { sw: 'part', text: tr('ui.st.thin'), sub: tr('ui.st.thin_sub') };
  if (c === 'b') return { sw: 'bare', text: dn != null && d > dn ? tr('ui.st.bare_since', { when: dk(dn) }) : tr('ui.st.bare'), sub: '' };
  return { sw: 'none', text: tr('ui.st.none'), sub: tr('ui.st.none_sub') };
}

/** OpenET measured crop water use from 1 Jan to the timeline month; the latest year with those months if this year is not out yet. */
export function measuredSoFar(oet: Extras['openet'], modelMonths: number[] | null, t: number) {
  if (!oet?.length) return null;
  const y = yearOf(t), m = Math.floor(dekadOf(t) / 3) + 1;
  const sum = (yy: number) => { const rows = oet.filter((r) => +r.month.slice(0, 4) === yy && +r.month.slice(5, 7) <= m); return rows.length === m ? rows.reduce((a, r) => a + r.in, 0) : null; };
  let yy = y, v = sum(y);
  while (v == null && yy > y - 3) { yy--; v = sum(yy); }
  if (v == null) return null;
  const model = (modelMonths ?? []).slice(0, m).reduce((a, x) => a + x, 0) / 25.4;
  return { inches: v, model, current: yy === y, label: `${MONTHS[0]}–${MONTHS[m - 1]} ${yy}` };
}
/** One sentence on crop-stress weeks for the season of the timeline date (or the latest season with checks). */
export function stressLine(ex: Extras, t: number) {
  const s = ex.stress;
  if (!s) return tr('ui.sl.notloaded');
  const years = Object.keys(s.evaluated).map(Number).filter((y) => y <= yearOf(t)).sort();
  const y = years[years.length - 1];
  if (y == null) return tr('ui.sl.none');
  const wk = s.weeks.filter((w) => w.start.startsWith(String(y)));
  if (!wk.length) return tr('ui.sl.noweeks', { y });
  const why: Record<string, number> = {};
  wk.forEach((w) => w.drivers.forEach((d) => (why[d] = (why[d] ?? 0) + 1)));
  const top = Object.entries(why).sort((a, b) => b[1] - a[1])[0]?.[0];
  return `${tr(wk.length === 1 ? 'ui.sl.weeks1' : 'ui.sl.weeksn', { n: wk.length, y })}${top ? `, ${tr('ui.sl.mostly', { why: DRIVER[top] ?? tr('ui.sl.unusual') })}` : ''}`;
}
export const DRIVER: Record<string, string> = { z_tmax: tr('ui.sl.d_heat'), z_eto: tr('ui.sl.d_air'), z_ndvi: tr('ui.sl.d_growth'), iforest: tr('ui.sl.d_mix') };
/** One sentence on standing water: the latest clear OPERA view up to the timeline date, plus the winter record. */
export function waterLine(ex: Extras, t: number) {
  const w = ex.water;
  if (!w) return tr('ui.wl.notloaded');
  const cut = `${yearOf(t)}-${String(Math.floor(dekadOf(t) / 3) + 1).padStart(2, '0')}-31`;
  const last = [...w.scenes].filter((s) => s.date <= cut).pop();
  const wet = w.seasons.filter((s) => s.seen).length, n = w.seasons.filter((s) => s.clear >= 5).length;
  const rec = n ? ` ${tr('ui.wl.rec', { wet, n })}` : '';
  return last ? `${tr('ui.wl.last', { date: fmtShort(last.date), what: last.frac >= 0.5 ? tr('ui.wl.under', { n: Math.round(last.frac * 100) }) : last.frac >= 0.1 ? tr('ui.wl.on', { n: Math.round(last.frac * 100) }) : tr('ui.wl.nowater') })}${rec}` : `${tr('ui.wl.noview')}${rec}`;
}

/** Rain so far this season: today from GET .../nasa_now (NASA GPM IMERG, normal 2001-2025), other dates from the daily record. */
export function rainNow(nasaNow: NasaNow | null, daily: Daily | null, t: number): RainSoFar | null {
  const nn = t === TODAY_T && nasaNow?.rainWyMm != null && nasaNow.rainWyNormalMm ? nasaNow : null;
  if (nn) return { period: { label: tr('ui.rn.label', { to: fmtShort(nn.rainDate!).replace(/ \d{4}$/, '') }), from: '', to: '', current: true }, inches: nn.rainWyMm! / 25.4, normal: nn.rainWyNormalMm! / 25.4, nSeasons: 25, pct: (nn.rainWyMm! / nn.rainWyNormalMm!) * 100, source: 'imerg' };
  return daily ? rainSoFar(daily, t) : null;
}
export type LoadState = 'loading' | 'ready' | 'timeout';
/** Thin loading line for one answer. */
const Skel = () => <span className="skel" aria-hidden="true" />;
/** The latest 10-day step with a clear satellite reading at or before t, at most 6 weeks back. */
export function latestClearT(cal: Calendar, t: number, maxBack = 4): number | null {
  for (let k = t; k >= 0 && t - k <= maxBack; k--) { const y = cal?.years?.[Math.floor(k / 36)]; const c = y?.rule?.[k % 36]; if (c && c !== 'u') return k; }
  return null;
}
/** One small reading: label, value, a bar with a reference mark. A number (`num`) counts up when it first appears and the
 *  bar grows to it; both glide when the date changes. The fill moves by transform only (styles.css, .m-fill). */
function Meter(m: { label: string; value: string | null; num?: { n: number; dec: number; unit: string }; state: LoadState; pct: number | null; mark: number | null; markLabel: string; note: string; warn?: boolean }) {
  return (
    <div className="meter">
      <span className="m-label">{m.label}</span>
      {m.value == null ? (m.state === 'timeout' ? <span className="m-val na">{tr('ui.na')}</span> : <><span className="skel skel-val" /><span className="skel skel-bar" /></>) : <>
        <span className="m-val" aria-label={m.value}>{m.num ? <><CountUp value={m.num.n} dec={m.num.dec} />{m.num.unit}</> : m.value}</span>
        <i className="m-track"><span className="m-clip">{m.pct != null && <em className={`m-fill ${m.warn ? 'warn' : ''}`} style={{ '--p': Math.max(0, Math.min(1, m.pct)) } as React.CSSProperties} />}</span>{m.mark != null && <b className="m-mark" style={{ left: `${Math.min(1, m.mark) * 100}%` }} title={m.markLabel} />}</i>
        <span className="m-note">{m.note}</span>
      </>}
    </div>
  );
}
export interface FieldNowProps { dataState: LoadState; dailyState: LoadState; thumb: { bbox: number[] } | null; extras: Extras; nasaNow: NasaNow | null; loc: Location; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; t: number; daily: Daily | null; prov: ProvMap }
export function FieldNow(p: FieldNowProps) {
  const { loc, cal, t } = p;
  const dt = cal ? latestClearT(cal, t) ?? dataT(cal, t) : t, behind = cal ? t > lastDataT(cal) : false;
  const ago = t - dt, agoText = ago <= 0 ? '' : ago === 1 ? `, ${tr('ui.ago.10d')}` : `, ${tr('ui.ago.w', { n: Math.round((ago * 10) / 7) })}`;
  const pend = (s: LoadState) => (s === 'timeout' ? <b className="na">{tr('ui.na_now')}</b> : <Skel />);
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
  const behindNote = dt < t ? ` ${tr('ui.fnow.latest', { when: whenT(dt), ago: agoText })}${yearOf(dt) < yr ? `; ${tr('ui.fnow.notproc', { yr })}` : ''}.` : '';
  const limit = p.allocation ?? null, needAf = need ? mmToAfac(need.value) : null, rainFed = !!base && isRainFed(base);
  const y26 = (cal?.years ?? []).find((y) => y.year === yr);
  const soil = soilFacts(loc.soil);
  // BC: California datasets this field lacks (a 404 shows one quiet line; an estimate shows normally, the reason under More detail)
  const bc = isBC(loc), gOpenet = bcGap(loc, 'openet'), gMl = bcGap(loc, 'ml_calendar');
  const openetEst = p.prov.openet?.origin === 'estimate';
  // a tapped spot: only its tier-1 sections are data; not_computed parts are hidden, unavailable ones get one quiet line
  const sp = loc.spot;
  const secOf = (k: string) => sp?.sections?.[k];
  const spotGap = (k: string) => { const x = secOf(k); return x && x.status !== 'ready' && x.status !== 'not_computed' ? <span className="gap-line">{x.reason ? `${x.reason.charAt(0).toUpperCase()}${x.reason.slice(1)}.` : tr('ui.fnow.spotna')}</span> : null; };
  return (
    <>
    <div className="glance" data-testid="glance">
      {!sp && (
      <div className="gl-top">
        <span className="gl-thumb">
          <img src={`${import.meta.env.BASE_URL}thumbs/${loc.id}.jpg`} alt="" onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }} />
          {p.thumb && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={loc.geometry.coordinates[0].map(([x, y]) => `${(((x - p.thumb!.bbox[0]) / (p.thumb!.bbox[2] - p.thumb!.bbox[0])) * 360).toFixed(1)},${(((p.thumb!.bbox[3] - y) / (p.thumb!.bbox[3] - p.thumb!.bbox[1])) * 240).toFixed(1)}`).join(' ')} /></svg>}
        </span>
        <span className="gl-season">
          <small>{tr('ui.fnow.sofar', { yr })}</small>
          <span className="gl-strip">
            {(y26?.rule ?? 'u'.repeat(36)).split('').map((c, k) => <em key={k} className={`c-${c}`} />)}
            <i className="gl-today" style={{ left: `${((dekadOf(t) + 0.5) / 36) * 100}%` }} title={whenT(t)} />
          </span>
          <span className="gl-months"><span>{MONTHS[0]}</span><span>{MONTHS[3]}</span><span>{MONTHS[6]}</span><span>{MONTHS[9]}</span></span>
          <b>{st ? st.text : '…'}</b>
        </span>
      </div>
      )}
      <div className={`gl-grid ${sp ? 'spot' : ''}`}>
        <Meter label={tr('ui.rain1oct')} value={rain ? `${fmtIn(rain.inches)} in` : null} num={rain ? { n: +fmtIn(rain.inches), dec: (fmtIn(rain.inches).split('.')[1] ?? '').length, unit: ' in' } : undefined} state={p.dailyState} pct={rain && rain.normal ? Math.min(1, rain.inches / (Math.max(rain.inches, rain.normal) * 1.25)) : null} mark={rain && rain.normal ? rain.normal / (Math.max(rain.inches, rain.normal) * 1.25) : null} markLabel={tr('ui.fnow.normal')} note={rain?.pct != null ? tr('ui.pct_normal', { n: Math.round(rain.pct) }) : ''} />
        <Meter label={tr('ui.fnow.waterneed')} value={needAf != null ? (rainFed ? RAIN_FED : `${needAf.toFixed(1)} ${tr('ui.u.afac')}`) : null} num={needAf != null && !rainFed ? { n: +needAf.toFixed(1), dec: 1, unit: ` ${tr('ui.u.afac')}` } : undefined} state={p.dataState} pct={needAf != null && limit ? rainFed ? 0 : Math.min(1, needAf / (Math.max(needAf, limit) * 1.2)) : null} mark={needAf != null && limit ? limit / (Math.max(needAf, limit) * 1.2) : null} markLabel={tr('ui.fnow.limit')} warn={needAf != null && limit != null && !rainFed && needAf > limit} note={limit != null ? `${tr('ui.fnow.limitn', { n: limit.toFixed(1) })}${p.exampleLimit ? ` ${tr('ui.fnow.example')}` : ''}` : ''} />
        {!sp && <Meter label={tr('ui.fnow.greenness')} value={fs && fs.cls !== 'u' ? fs.ndvi.toFixed(2) : null} num={fs && fs.cls !== 'u' ? { n: +fs.ndvi.toFixed(2), dec: 2, unit: '' } : undefined} state={p.dataState} pct={fs && fs.cls !== 'u' ? Math.max(0, Math.min(1, fs.ndvi)) : null} mark={0.6} markLabel={tr('ui.fnow.fullcanopy')} note={fs && fs.cls !== 'u' ? cap(whenT(dt)) : ''} />}
        {!sp && (
        <div className="meter">
          <span className="m-label">{tr('ui.fnow.soilgw')}</span>
          {!p.regional ? (p.dataState === 'timeout' ? <span className="m-val na">{tr('ui.na')}</span> : <><span className="skel skel-bar" /><span className="skel" /></>) : <>
            <span className="m-dots">
              {/* each dot rides a full-width rail that slides out from the middle (normal) to its percentile, by transform */}
              <i className="m-track"><em className="m-mid" />{smap != null && <span className="dot-rail" style={{ '--x': smap } as React.CSSProperties}><b className="dot soil" title={tr('ui.fnow.soilp', { o: ord(Math.round(smap)) })} /></span>}{grace != null && <span className="dot-rail" style={{ '--x': grace } as React.CSSProperties}><b className="dot gw" title={tr('ui.fnow.gwp', { o: ord(Math.round(grace)) })} /></span>}</i>
            </span>
            <span className="m-note"><i className="k soil" />{tr('ui.fnow.soil')} {smap != null ? ord(Math.round(smap)) : '–'}, <i className="k gw" />{tr('ui.fnow.gwl')} {grace != null ? ord(Math.round(grace)) : '–'}</span>
          </>}
        </div>
        )}
      </div>
    </div>
    <ThisWeek loc={loc} />
    <dl className="answers">
      {sp ? <SpotCrop loc={loc} /> : (
      <div className="ans">
        <dt>{tr('ui.fnow.q_growing')}</dt>
        <dd>
          {st ? <b><i className={`sw-${st.sw}`} />{st.text}</b> : pend(p.dataState)}
          <span className="d-only">{crop ? tr('ui.fnow.onrecord', { crop: cropName(crop), yr }) : tr('ui.fnow.nomap', { yr, who: bc ? 'AAFC' : 'USDA', next: yr + 1, last: lastRec, crop: cropName(loc.crop_history[lastRec]).toLowerCase() })} {st?.sub}</span>
        </dd>
      </div>
      )}
      {!sp && (
      <div className="ans d-only">
        <dt>{tr('ui.fnow.q_green')} <What k="greenness" /></dt>
        <dd>
          {fs && fs.cls !== 'u' && fs.cls !== 'w' ? <>
            <b>{fs.ndvi >= 0.6 ? tr('ui.fnow.g_full') : fs.ndvi >= 0.35 ? tr('ui.fnow.g_part') : fs.ndvi >= 0.2 ? tr('ui.fnow.g_thin') : tr('ui.fnow.g_little')}</b>
            <span>{tr('ui.fnow.g_scale', { n: fs.ndvi.toFixed(2) })}</span>
          </> : !cal ? pend(p.dataState) : <b>{fs?.cls === 'w' ? tr('ui.fnow.g_water') : tr('ui.fnow.g_noview')}</b>}
          <cite>{tr('ui.fnow.g_from', { src: calSourceShort(p.prov.calendar), when: whenT(dt), ago: agoText })} <Src p={p.prov.calendar} /></cite>
        </dd>
      </div>
      )}
      <div className="ans">
        <dt>{tr('ui.fnow.q_rain')}</dt>
        <dd>
          {rain ? <>
            <b>{rain.period.current ? '' : `${tr('ui.fnow.r_none')} `}{rain.pct != null ? tr(rain.period.current ? 'ui.fnow.r_sofar' : 'ui.fnow.r_last', { what: vsNormal(rain.pct, tr('ui.fnow.wetter'), tr('ui.fnow.drier')) }) : ''}</b>
            <span>{fmtIn(rain.inches)} in {rain.period.current ? tr('ui.fnow.since1oct') : rain.period.label}.{rain.normal != null ? ` ${tr('ui.fnow.normal_in', { n: fmtIn(rain.normal) })}` : ''}</span>
            <cite>{rain.source === 'imerg' ? tr('ui.fnow.src_imerg') : rain.source === 'power' ? tr('ui.fnow.src_power') : tr('ui.fnow.src_stations', { s: stationsName(loc) })}; {tr('ui.fnow.normdef', { n: rain.nSeasons })} <Src p={p.prov.daily} /></cite>
          </> : pend(p.dailyState)}
        </dd>
      </div>
      <div className="ans d-only">
        <dt>{tr('ui.fnow.q_used')} <What k="et" /></dt>
        <dd>
          {ms && ms.current ? <>
            <b>{tr(openetEst ? 'ui.fnow.u_est' : 'ui.fnow.u_meas', { n: fmtIn(ms.inches) })}</b>
            <span>{tr(openetEst ? 'ui.fnow.u_sub_est' : 'ui.fnow.u_sub_meas', { label: ms.label, model: fmtIn(ms.model), af: mmToAfac(ms.inches * 25.4).toFixed(1) })}</span>
            <cite>{tr('ui.fnow.u_cite')} <Src p={p.prov.openet} /></cite>
            <GapLine gap={gOpenet} missing={false} />
          </> : cw ? <>
            <b>{cw.period.current ? tr('ui.fnow.c_sofar') : tr('ui.fnow.c_last')}: {vsNormal(cw.pct, tr('ui.fnow.more'), tr('ui.fnow.less'))}</b>
            <span>{tr('ui.fnow.c_sub', { n: fmtIn(cw.inches), label: cw.period.label, normal: fmtIn(cw.normal), af: mmToAfac(cw.inches * 25.4).toFixed(1) })}{ms ? ` ${tr(openetEst ? 'ui.fnow.c_est' : 'ui.fnow.c_meas', { label: ms.label, n: fmtIn(ms.inches), model: fmtIn(ms.model) })}` : ''}</span>
            <GapLine gap={gOpenet} missing={!p.extras.openet} />
          </> : !p.strategies || !p.daily ? pend(p.daily ? p.dataState : p.dailyState) : <b>{tr('ui.fnow.norot')}</b>}
          {sp && spotGap('openet')}
        </dd>
      </div>
      {need && (
        <div className="ans">
          <dt>{tr('ui.fnow.q_limit')} <What k="waterBalance" /></dt>
          <dd>
            <b>{rainFed ? tr('ui.fnow.fitsany') : p.allocation == null ? tr('ui.fnow.about_af', { n: mmToAfac(need.value).toFixed(1) }) : mmToAfac(need.value) > p.allocation ? tr('ui.fnow.shortby', { n: (mmToAfac(need.value) - p.allocation).toFixed(1) }) : tr('ui.fnow.fitslimit')}</b>
            <span>{rainFed ? `${RAIN_FED}.` : tr('ui.fnow.needs', { n: mmToAfac(need.value).toFixed(1) })}{p.allocation != null ? ` ${tr('ui.fnow.limitc', { n: p.allocation.toFixed(1) })}` : ''}{p.exampleLimit && <em className="status example ex-limit">{tr('ui.fnow.exchange')}</em>}</span>
            {!rainFed && <span className="d-only">{tr('ui.fnow.likely', { lo: mmToAfac(need.low ?? need.value).toFixed(1), hi: mmToAfac(need.high ?? need.value).toFixed(1) })}</span>}
            <cite>{tr('ui.fnow.l_cite')} <Src p={p.prov.strategies} /></cite>
            {sp && loc.region === 'other' && <span className="gap-line">{tr('ui.fnow.outside', { fam: loc.family === 'rice' ? tr('ui.pk.rice').toLowerCase() : tr('ui.pk.forage').toLowerCase() })}</span>}
          </dd>
        </div>
      )}
      {!sp && (
      <div className="ans">
        <dt>{tr('ui.fnow.q_soil')} <What k="soilAnomaly" /></dt>
        <dd>
          {!p.regional ? pend(p.dataState) : <b>{smap == null ? tr('ui.fnow.nosoil') : band(smap, tr('ui.fnow.s_wet'), tr('ui.fnow.s_norm'), tr('ui.fnow.s_dry'))}; {grace == null ? tr('ui.fnow.nogw') : band(grace, tr('ui.fnow.g_more'), tr('ui.fnow.g_norm'), tr('ui.fnow.g_less')).toLowerCase()}</b>}
          <span className="d-only">{smap != null && `${tr('ui.fnow.sp', { o: ord(Math.round(smap)) })}${sm && sm.t < t - 1 ? ` (${tr('ui.fnow.latest_p', { when: whenT(sm.t) })})` : ''}; ${tr('ui.fnow.fifty')} `}{grace != null && `${tr('ui.fnow.gp', { o: ord(Math.round(grace)) })}${gr && gr.t < t - 1 ? ` (${tr('ui.fnow.latest_p', { when: whenT(gr.t) })})` : ''}, ${tr('ui.fnow.basin')}`}</span>
          <cite>{p.regionalLive.soilSource === 'grace_da' ? 'NASA GRACE-FO' : tr('ui.fnow.smapgrace')}. <Src p={p.prov.regional} /></cite>
        </dd>
      </div>
      )}
      {soil.mix || soil.texture || soil.holds || soil.drains || soil.salt ? (
        <div className="ans" data-testid="soil-answer">
          <dt>{tr('ui.fnow.q_soillike')}</dt>
          <dd>
            {soil.texture && <b>{soil.texture}</b>}
            {soil.mix && <SoilBar mix={soil.mix} />}
            {(soil.holds || soil.drains || soil.salt) && <span className="soil-facts">{[soil.holds, soil.drains, soil.salt].filter(Boolean).join(' ')}</span>}
            {soil.rotation && <span className="soil-rot">{soil.rotation}</span>}
            <cite>{soil.source}. <Src p={p.prov.soil} /></cite>
          </dd>
        </div>
      ) : null}
      {!sp && (
      <div className="ans d-only">
        <dt>{tr('ui.fnow.q_stress')} <What k="stress" /></dt>
        <dd>
          {p.dataState !== 'ready' ? pend(p.dataState) : gMl && !p.extras.stress ? <>
            <GapLine gap={gMl} missing />
            {p.extras.water && <span>{waterLine(p.extras, t)}</span>}
          </> : <><b>{stressLine(p.extras, t)}</b>
          {(!bc || p.extras.water) && <span>{waterLine(p.extras, t)}</span>}
          {gMl && <GapLine gap={gMl} missing={false} />}</>}
          {!(gMl && !p.extras.stress) && <cite>{tr('ui.fnow.stress_cite')} <Src p={p.prov.stress ?? p.prov.water_seen} /></cite>}
        </dd>
      </div>
      )}
      {!sp ? (
      <div className="ans d-only">
        <dt>{tr('ui.fnow.q_heat')} <What k="frost" /></dt>
        <dd>
          {hf ? <>
            <b>{tr(hf.hot === 1 ? 'ui.fnow.h_day' : 'ui.fnow.h_days', { n: hf.hot, f: HOT_F })} {hf.period.current ? tr('ui.fnow.h_sofar') : tr('ui.fnow.h_in', { label: hf.period.label.replace('last year, ', '') })}</b>
            <span>{tr('ui.fnow.h_sub', { hn: hf.hotNormal != null ? Math.round(hf.hotNormal) : '?', label: hf.frostPeriod.label, n: hf.frost, fn: hf.frostNormal != null ? Math.round(hf.frostNormal) : '?' })}</span>
            <cite>{stationsName(loc)}. {tr('ui.fnow.h_power', { why: bc ? tr('ui.fnow.h_bc') : tr('ui.fnow.h_ca') })} <Src p={p.prov.daily} /></cite>
          </> : pend(p.dailyState)}
        </dd>
      </div>
      ) : <div className="ans d-only"><dt>{tr('ui.fnow.q_heat0')}</dt><dd><span className="gap-line">{tr('ui.fnow.h_spot')}</span></dd></div>}
    </dl>
    </>
  );
}

/** A tapped spot: what the crop map says was grown here (USDA Cropland Data Layer at points inside the spot). */
function SpotCrop({ loc }: { loc: Location }) {
  const sp = loc.spot!, sec = sp.sections?.crop_history;
  const ys = Object.keys(loc.crop_history).map(Number).sort((a, b) => a - b), last = ys[ys.length - 1];
  const now = last != null ? cropName(loc.crop_history[last]) : null, nowKey = last != null ? cropKey(loc.crop_history[last]) : null;
  const ten = ys.slice(-10), same = now ? ten.filter((y) => cropName(loc.crop_history[y]) === now).length : 0;
  return (
    <div className="ans" data-testid="spot-crop">
      <dt>{tr('ui.fnow.q_grown')}</dt>
      <dd>
        {sp.state === 'loading' ? <span className="skel" aria-hidden="true" /> : now ? <>
          <b>{tr('ui.crop_in', { crop: now, year: last })}</b>
          <span>{nowKey === 'Left fallow' ? tr('ui.nt.fallow', { year: last }) + '.' : tr('ui.rec.in', { crop: now, n: same, total: ten.length }) + '.'}</span>
        </> : <span className="gap-line">{sec?.reason ?? tr('ui.fnow.nocrop')}</span>}
        <cite>{tr('ui.fnow.cdl', { what: loc.mine ? tr('ui.fnow.outline') : tr('ui.fnow.spot') })}</cite>
      </dd>
    </div>
  );
}

/** What happened on this field in the last 3 seasons, one line each. */
export function LastSeasons({ loc, cal, t }: { loc: Location; cal: Calendar | null; t: number }) {
  if (!cal) return null;
  const last = yearOf(lastDataT(cal));
  const ys = (cal?.years ?? []).filter((y) => y.year <= last && y.year > last - 3).reverse();
  return (
    <ul className="seasons">
      {ys.map((y) => {
        const n = (c: string) => y.rule.split('').filter((x) => x === c).length * 10;
        const cr = cropName(loc.crop_history[y.year]);
        return (
          <li key={y.year}>
            <b>{y.year}</b>
            <span>{cr}. {tr('ui.fnow.ls', { c: n('c'), p: n('p'), b: n('b'), w: n('w') })}{n('u') ? `, ${tr('ui.fnow.ls_u', { n: n('u') })}` : ''}.</span>
            <i className="mini-strip">{y.rule.split('').map((c, i) => <em key={i} className={`c-${c}`} />)}</i>
          </li>
        );
      })}
      {yearOf(t) > last && <li className="dim"><b>{yearOf(t)}</b><span>{tr('ui.fnow.ls_not', { y: yearOf(t) })}</span></li>}
    </ul>
  );
}
