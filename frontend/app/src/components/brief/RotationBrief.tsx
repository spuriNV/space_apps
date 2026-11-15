// Printable one-page brief, written for the grower and adviser: what the field is, what's likely this season,
// the option chosen, what it gains and gives up, what to check locally, and sources. No scores as headlines.
import { useState } from 'react';
import type { Calendar, CoverClass, Location, RotationStrategy, Source } from '../../types';
import type { NasaNow, Outlook, ProvMap } from '../../api';
import type { Daily } from '../../season';
import { bareWindow, fmtIn } from '../../season';
import { rainNow } from '../ui/FieldNow';
import { CLASS_COLOR, MONTHS, TODAY_T, isRainFed, lastDataT, mmToAfac, RAIN_FED, yearOf } from '../../lib';
import Icon from '../Icons';
import { Src, cleanSoil, stateFieldNo, fieldName, acres, county, cropName, openetText } from '../ui/shared';
import { fieldCtx, tradeoffs, HEAT_NOTE } from '../compare/ComparePanel';
import { BARE_DEF, observedBare, usuallyBareMonths } from '../../bare';
import { t, tx } from '../../i18n';

const lean = (c?: { category: string; prob: number | null } | null) => (!c || c.category.startsWith('equal') || (c.prob ?? 40) <= 35 ? t('ui.br.lean0') : c.category.startsWith('above') ? t('ui.br.leanwet') : t('ui.br.leandry'));
/** Engine review notes are written for the team; strip spec references and convert mm to acre-feet per acre. */
// the API strips internal markers ((U), spec refs) from user-facing text; only the unit conversion is left here
const plain = (s: string) => s.replace(/(\d[\d,]*)\s?mm/g, (_, n) => `${(Number(n.replace(/,/g, '')) / 304.8).toFixed(1)} ${t('ui.u.afac')}`);
const SEASON: Record<string, string> = { NDJ: t('ui.br.NDJ'), DJF: t('ui.br.DJF'), JFM: t('ui.br.JFM'), FMA: t('ui.br.FMA') };

export default function RotationBrief(p: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; allocation: number; exampleLimit: boolean; prov: ProvMap; outlook: Outlook | null; nasaNow: NasaNow | null; cal: Calendar | null; daily: Daily | null; onClose: () => void; /** false: kept in the page for printing only (step 5's Print button), not shown */ preview?: boolean }) {
  const { loc, strategies } = p;
  const s = strategies.find((x) => x.id === p.pick) ?? strategies.find((x) => !x.is_baseline) ?? strategies[0];
  const base = strategies.find((x) => x.is_baseline) ?? strategies[0];
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  if (!s) return null;
  const sources: Source[] = [];
  const cite = (src?: Source | null) => {
    if (!src?.id || src.id === 'mock') return null;
    let i = sources.findIndex((x) => x.id === src.id);
    if (i < 0) { sources.push(src); i = sources.length - 1; }
    return <sup className="cite" title={src.title}>{i + 1}</sup>;
  };
  const need = s.water.irrigation_need_mm, needB = base.water.irrigation_need_mm;
  const afv = (v: number | null | undefined) => (v == null ? '–' : mmToAfac(v).toFixed(1));
  const rainFed = isRainFed(s), baseRainFed = isRainFed(base);
  const over = !rainFed && mmToAfac(need.low ?? need.value) > p.allocation, within = rainFed || mmToAfac(need.high ?? need.value) <= p.allocation;
  const ctx = fieldCtx(strategies, p.daily, p.cal);
  const tr = s.is_baseline ? null : tradeoffs(base, s, ctx, strategies, loc.soil.hydrologic_group === 'D');
  const ob = observedBare(p.cal), bareWhen = usuallyBareMonths(p.cal);
  const upper = /safflower|wheat/i.test(s.name);
  const limitWord = p.exampleLimit ? ` ${t('ui.br.exlimit')}` : '';
  const last = p.cal ? yearOf(lastDataT(p.cal)) : 2025;
  const recent = [last - 2, last - 1, last].map((y) => `${y} ${loc.crop_history[y] ? cropName(loc.crop_history[y]).toLowerCase() : t('ui.br.nomap')}`).join(', ');
  const bc = loc.region === 'bc';
  const soil = cleanSoil(loc.soil), awc = soil.awc_mm_per_m?.value, inFt = awc != null ? (awc / 1000) * 12 : null, saline = (soil.ec_ds_per_m ?? 0) >= 4;
  const o = p.outlook, rain = rainNow(p.nasaNow, p.daily, TODAY_T);
  const bw = p.cal ? bareWindow(p.cal, p.daily, (p.cal.years ?? []).map((y) => y.year).filter((y) => y >= 2016 && y <= 2025)) : null;
  const wet = o?.seasons.filter((x) => x.rain?.category.startsWith('above')).length ?? 0;
  const res = o?.reservoirs[0];
  const review = s.brief.local_review ?? [];
  const checks = (s.constraints_check ?? []).filter((c) => c.status !== 'ok');

  return (
    <div className={`briefwrap ${p.preview === false ? 'print-only' : ''}`} role="dialog" aria-label={t('ui.br.aria')} aria-hidden={p.preview === false} data-testid="brief">
      <div className="brief-stage">
        <article className="paper">
          <header className="p-head">
            <div>
              <div className="p-kicker">{t('ui.br.kicker')}</div>
              <h1>{fieldName(loc)}</h1>
              <div className="p-sub">{t('ui.n_acres', { n: acres(loc) })}, {bc ? `${county(loc)}, ${t('ui.place.bc')}` : `${t('ui.place.county', { name: county(loc) })}, California · ${stateFieldNo(loc).toLowerCase()}`}</div>
            </div>
            <div className="p-option"><span>{t('ui.br.option')}</span><b>{s.short_name}</b>{s.is_baseline && <em>{t('ui.br.now')}</em>}</div>
          </header>

          <div className="p-cols">
            <section>
              <h2>1. {t('ui.br.h1')}</h2>
              <p>{soil.muname || soil.texture_class ? <>{soil.muname ? soil.muname.split(',')[0] : soil.texture_class}{[soil.drainage_class?.toLowerCase(), inFt != null ? t('ui.br.holds', { n: inFt.toFixed(1) }) : null].filter(Boolean).length ? ': ' : ''}{[soil.drainage_class?.toLowerCase(), inFt != null ? t('ui.br.holds', { n: inFt.toFixed(1) }) : null].filter(Boolean).join(', ')}{saline ? `, ${t('ui.br.salty')}` : ''}.</> : null}{cite(loc.area_ha.source)} {bc ? t('ui.br.water_bc', { ws: loc.water_context?.watershed.split(';')[0] ?? t('ui.br.nows'), years: loc.water_context?.orders.map((x) => x.date.slice(0, 4)).join(', ') || t('ui.br.dryyears') }) : t(loc.water.source === 'surface' ? 'ui.br.water_sw' : 'ui.br.water_gw')} {t('ui.br.last3', { recent })} {ob && ob.years?.length ? t('ui.br.bare', { n: ob.value, when: bareWhen, from: ob.years[0], to: ob.years[ob.years.length - 1] }) : ''} {openetText(strategies)}{cite(base.water.etc_vs_openet_pct?.source)}</p>
            </section>
            <section>
              <h2>2. {t('ui.br.h2')} <small>{t('ui.br.h2s')}</small></h2>
              <ul className="p-list">
                {o && o.seasons.length > 0 && <li>{t('ui.br.noaa')} {o.seasons.slice(0, 3).map((x) => `${SEASON[x.season] ?? x.season} ${lean(x.rain)}`).join('; ')}.</li>}
                {o?.droughtOutlook && <li>{t('ui.br.drought')} {o.droughtNow ? (o.droughtNow.category.startsWith('None') ? t('ui.br.nodrought') : t('ui.br.dnow', { c: o.droughtNow.category.replace(/^D\d /, '').toLowerCase() })) : ''}; {t('ui.br.dthrough', { c: o.droughtOutlook.category === 'No_Drought' ? t('ui.br.none') : o.droughtOutlook.category.toLowerCase(), target: o.droughtOutlook.target })}</li>}
                {res && <li>{t('ui.br.res', { name: res.name.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()), v: res.pctAvg != null ? t('ui.br.pctavg', { n: Math.round(res.pctAvg) }) : t('ui.br.unknown') })}</li>}
                {rain && <li>{t('ui.br.rain', { label: rain.period.label, n: fmtIn(rain.inches), pct: rain.pct != null ? t('ui.pct_normal', { n: Math.round(rain.pct) }) : '' })}</li>}
                {o?.bare ? (o.bare.start ? <li>{t('ui.br.barestretch', { from: o.bare.start, to: o.bare.end, n: Math.round(o.bare.chance ?? 0) })}{wet ? `, ${t('ui.br.leanswet')}` : ''}.</li>
                  : <li>{t('ui.br.covered')}</li>) : bw && bw.days > 0 ? <li>{t('ui.br.barestretch2', { from: bw.from, to: bw.to, hits: bw.hits, winters: bw.winters })}{wet ? `, ${t('ui.br.leanswet')}` : ''}.</li> : <li>{t('ui.br.covered')}</li>}
              </ul>
            </section>
          </div>

          <section>
            <h2>3. {t('ui.br.h3')} {s.name.replace(/ \(current\)/, '')}</h2>
            <div className="p-months">{s.month_cover.split('').map((c, i) => <div key={i}><span>{MONTHS[i]}</span><i style={{ background: CLASS_COLOR[c as CoverClass] }} /><em>{s.calendar_months[i]}</em></div>)}</div>
            <p className="p-water">{rainFed ? <b>{RAIN_FED}</b> : <>{t('ui.br.need')} <b>{t('ui.br.af', { n: afv(need.value) })}</b> {t('ui.br.ayear')}{upper ? '*' : ''}</>}{s.is_baseline ? '' : baseRainFed ? `, ${t('ui.br.against_none')}` : `, ${t('ui.br.against', { n: afv(needB.value), u: rainFed ? ` ${t('ui.br.afunit')}` : '' })}`}. {t('ui.br.yourlimit', { n: p.allocation.toFixed(1), word: limitWord })} <b className={over ? 'st bad' : within ? 'st good' : 'st warn'}>{over ? t('ui.br.over') : rainFed ? t('ui.fnow.fitsany').toLowerCase() : within ? t('ui.br.fits') : t('ui.br.mayover')}</b>.{cite(need.source)}{rainFed ? '' : <> {t('ui.br.dry22', { n: afv(s.exposure.replay['2022']?.irrigation_need_mm.value) })}</>}</p>
          </section>

          {tr && (
            <div className="p-cols">
              <section><h2>4. {t('ui.br.gains')}</h2><ul className="p-list gain">{tr.gains.map((g) => <li key={g}>{g}</li>)}{!tr.gains.length && <li>{t('ui.br.nobetter')}</li>}</ul></section>
              <section><h2>{t('ui.br.gives')}</h2><ul className="p-list loss">{tr.losses.map((g) => <li key={g}>{g}</li>)}{!tr.losses.length && <li>{t('ui.br.noworse')}</li>}</ul>
                {tr.unclear.length > 0 && <p className="p-note">{t('ui.br.toclose', { list: tr.unclear.join(', ') })}</p>}</section>
            </div>
          )}

          <section>
            <h2>{tr ? '5' : '4'}. {t('ui.br.glance')} <small>{t('ui.br.typical')}</small></h2>
            <table className="p-table">
              <thead><tr><th>{t('ui.br.th1')}</th><th>{t('ui.br.th2')}</th><th>{t('ui.br.th3')}</th><th>{t('ui.br.th4')}</th><th>{t('ui.br.th5')}</th></tr></thead>
              <tbody>{strategies.map((x) => { const nd = x.water.irrigation_need_mm, bd = ctx.bare[x.id]?.v ?? x.exposure.bare_days_per_year.value, hb = ctx.heat[x.id]?.v; const rf = isRainFed(x), ov = !rf && mmToAfac(nd.low ?? nd.value) > p.allocation, ok = rf || mmToAfac(nd.high ?? nd.value) <= p.allocation; return (
                <tr key={x.id} className={x.id === s.id ? 'pick' : ''}><th>{x.short_name}{x.is_baseline ? ` (${t('ui.brief.today')})` : ''}</th><td>{rf ? RAIN_FED : <>{afv(nd.value)} ({afv(nd.low)}–{afv(nd.high)}){/safflower|wheat/i.test(x.name) ? '*' : ''}</>}</td><td>{ov ? t('ui.br.over_s') : ok ? t('ui.br.fits') : t('ui.br.mayover')}</td><td>{Math.round(bd)}{x.is_baseline && ctx.bare[x.id] ? ` ${t('ui.br.seen')}` : ` ${t('ui.br.est')}`}</td><td>{hb != null ? hb.toFixed(1) : '–'}</td></tr>); })}</tbody>
            </table>
            <p className="p-note">{t('ui.br.tnote')}</p>
          </section>

          <section>
            <h2>{tr ? '6' : '5'}. {t('ui.br.check')}</h2>
            <ul className="p-review">
              {checks.map((c) => <li key={c.constraint}><label><input type="checkbox" /><span>{plain(c.detail)}</span></label></li>)}
              {review.map((r) => <li key={r.item}><label><input type="checkbox" checked={!!ticks[r.item]} onChange={(e) => setTicks({ ...ticks, [r.item]: e.target.checked })} /><span>{plain(r.item)}</span></label>{r.severity === 'high' && <em className="sev high">{t('ui.br.important')}</em>}</li>)}
              <li><label><input type="checkbox" /><span>{bc ? t('ui.br.chk_bc') : t('ui.br.chk_ca')}</span></label></li>
              <li><label><input type="checkbox" /><span>{t('ui.br.chk_seed')}</span></label></li>
            </ul>
          </section>

          <footer className="p-foot">
            <div className="p-sources"><b>{t('ui.src.title')}</b>
              {sources.map((src, i) => <span key={src.id}>{i + 1}. {src.title ?? src.id}{src.verified ? '' : ` (${t('ui.br.unverified')})`}</span>)}
              <span>{t('ui.br.nasa')} {bc ? <>{t('ui.br.src_bc')} {BARE_DEF} {HEAT_NOTE.replace('NOAA', 'Environment Canada')}</> : <>{t('ui.br.src_ca')} {BARE_DEF} {HEAT_NOTE}</>}</span>
            </div>
            <div className="p-disclaimer">{t('ui.br.disclaimer')}</div>
            <div>{t('ui.br.made')}</div>
          </footer>
        </article>
      </div>

      <aside className="brief-rail glass">
        <div className="br-head"><h2>{t('ui.br.prev')}</h2><button className="icon-btn" onClick={p.onClose} title={t('ui.br.closeprev')} aria-label={t('ui.br.closeprev')}><Icon name="close" size={16} /></button></div>
        <p className="muted">{t('ui.act.brief_s')}. <Src p={p.prov.strategies} /></p>
        <label className="br-field"><span>{t('ui.br.optprint')}</span>
          <select value={s.id} onChange={(e) => p.setPick(e.target.value)} data-testid="brief-pick">{strategies.map((x) => <option key={x.id} value={x.id}>{x.short_name}{x.is_baseline ? ` (${t('ui.brief.today')})` : ''}</option>)}</select>
        </label>
        <p className="muted">{t('ui.br.templates')}</p>
        <button className="btn btn-primary wide" onClick={() => window.print()}><Icon name="brief" size={16} />{t('ui.brief.print')}</button>
      </aside>
    </div>
  );
}
