// Printable one-page brief, written for the grower and adviser: what the field is, what's likely this season,
// the option chosen, what it gains and gives up, what to check locally, and sources. No scores as headlines.
import { useState } from 'react';
import type { Calendar, CoverClass, Location, RotationStrategy, Source } from '../../types';
import type { NasaNow, Outlook, ProvMap } from '../../api';
import type { Daily } from '../../season';
import { bareWindow, fmtIn } from '../../season';
import { rainNow } from '../ui/FieldNow';
import { CLASS_COLOR, MONTHS, TODAY_T, lastDataT, mmToAfac, yearOf } from '../../lib';
import Icon from '../Icons';
import { Src, Workflow, fieldCode, fieldName, acres, placeLabel, cropName, openetText, isBC } from '../ui/shared';
import { fieldCtx, tradeoffs, HEAT_NOTE } from '../compare/ComparePanel';
import { BARE_DEF, observedBare, usuallyBareMonths } from '../../bare';

const lean = (c?: { category: string; prob: number | null } | null) => (!c || c.category.startsWith('equal') || (c.prob ?? 40) <= 35 ? 'no clear lean' : c.category.startsWith('above') ? 'leans wetter than normal' : 'leans drier than normal');
/** Engine review notes are written for the team; strip spec references and convert mm to acre-feet per acre. */
const plain = (t: string) => t.replace(/\s*\((spec [^)]*|U)\)/g, '').replace(/(\d[\d,]*)\s?mm/g, (_, n) => `${(Number(n.replace(/,/g, '')) / 304.8).toFixed(1)} acre-ft/acre`);
const SEASON: Record<string, string> = { NDJ: 'Nov–Jan', DJF: 'Dec–Feb', JFM: 'Jan–Mar', FMA: 'Feb–Apr' };

export default function RotationBrief(p: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; allocation: number; exampleLimit: boolean; prov: ProvMap; outlook: Outlook | null; nasaNow: NasaNow | null; cal: Calendar | null; daily: Daily | null; onClose: () => void }) {
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
  const over = mmToAfac(need.low ?? need.value) > p.allocation, within = mmToAfac(need.high ?? need.value) <= p.allocation;
  const ctx = fieldCtx(strategies, p.daily, p.cal);
  const tr = s.is_baseline ? null : tradeoffs(base, s, ctx, strategies, loc.soil.hydrologic_group === 'D');
  const ob = observedBare(p.cal), bareWhen = usuallyBareMonths(p.cal);
  const upper = /safflower|wheat/i.test(s.name);
  const limitWord = p.exampleLimit ? ' (an example limit; write in yours)' : '';
  const last = p.cal ? yearOf(lastDataT(p.cal)) : 2025;
  const recent = [last - 2, last - 1, last].map((y) => `${y} ${loc.crop_history[y] ? cropName(loc.crop_history[y]).toLowerCase() : '(crop map not out yet)'}`).join(', ');
  const soil = loc.soil, inFt = (soil.awc_mm_per_m.value / 1000) * 12, saline = (soil.ec_ds_per_m ?? 0) >= 4;
  const o = p.outlook, rain = rainNow(p.nasaNow, p.daily, TODAY_T);
  const bw = p.cal ? bareWindow(p.cal, p.daily, p.cal.years.map((y) => y.year).filter((y) => y >= 2016 && y <= 2025)) : null;
  const wet = o?.seasons.filter((x) => x.rain?.category.startsWith('above')).length ?? 0;
  const res = o?.reservoirs[0];
  const review = s.brief.local_review ?? [];
  const checks = (s.constraints_check ?? []).filter((c) => c.status !== 'ok');

  return (
    <div className="briefwrap" role="dialog" aria-label="Summary for your adviser" data-testid="brief">
      <div className="brief-stage">
        <article className="paper">
          <header className="p-head">
            <div>
              <div className="p-kicker">CropLytics summary for the grower and adviser · prepared 14 Nov 2026</div>
              <h1>{fieldName(loc)}</h1>
              <div className="p-sub">{acres(loc)} acres, {placeLabel(loc)} · {fieldCode(loc).startsWith('DWR') ? fieldCode(loc).replace('DWR ', 'state field no. ') : fieldCode(loc)}</div>
            </div>
            <div className="p-option"><span>Option looked at</span><b>{s.short_name}</b>{s.is_baseline && <em>what the field does now</em>}</div>
          </header>

          <div className="p-cols">
            <section>
              <h2>1. This field</h2>
              <p>{soil.muname.split(',')[0]}: {soil.drainage_class.toLowerCase()}, holds about {inFt.toFixed(1)} in of water per foot of soil{saline ? ', salty enough to limit salt-sensitive crops' : ''}.{cite(loc.area_ha.source)} Water from {isBC(loc) ? (loc.water.district || 'Lower Salmon River surface licences') : loc.water.source === 'surface' ? 'a surface-water district' : 'wells, under a groundwater allocation'}. Last three seasons: {recent}. {ob ? `Bare about ${ob.value} days a year, mostly ${bareWhen} (satellite, ${ob.years[0]}–${ob.years[ob.years.length - 1]}).` : ''} {openetText(strategies, loc)}{cite(base.water.etc_vs_openet_pct?.source)}</p>
            </section>
            <section>
              <h2>2. What’s likely this season <small>outlooks, not forecasts</small></h2>
              <ul className="p-list">
                {o && o.seasons.length > 0 && <li>NOAA’s rain outlook: {o.seasons.slice(0, 3).map((x) => `${SEASON[x.season] ?? x.season} ${lean(x.rain)}`).join('; ')}.</li>}
                {o?.droughtOutlook && <li>Drought: {o.droughtNow ? (o.droughtNow.category.startsWith('None') ? 'no drought now' : `${o.droughtNow.category.replace(/^D\d /, '').toLowerCase()} now`) : ''}; {o.droughtOutlook.category === 'No_Drought' ? 'none expected' : o.droughtOutlook.category.toLowerCase()} through {o.droughtOutlook.target}.</li>}
                {res && <li>{res.name.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())} reservoir is at {res.pctAvg != null ? `${Math.round(res.pctAvg)}% of average` : 'unknown'} for the date.</li>}
                {rain && <li>Rain {rain.period.label}: {fmtIn(rain.inches)} in, {rain.pct != null ? `${Math.round(rain.pct)}% of normal` : ''} (NASA GPM IMERG satellite rain).</li>}
                {o?.bare ? (o.bare.start ? <li>Longest bare stretch in winter: usually {o.bare.start} to {o.bare.end}; a 1-inch rain day landed in it in {Math.round(o.bare.chance ?? 0)}% of past winters{wet ? ', and the outlook leans wet' : ''}.</li>
                  : <li>Usually covered or flooded all winter: no regular bare stretch.</li>) : bw && bw.days > 0 ? <li>Longest bare stretch in winter: usually {bw.from} to {bw.to}; a 1-inch rain day fell in that window in {bw.hits} of the last {bw.winters} winters{wet ? ', and the outlook leans wet' : ''}.</li> : <li>Usually covered or flooded all winter: no regular bare stretch.</li>}
              </ul>
            </section>
          </div>

          <section>
            <h2>3. The option: {s.name.replace(/ \(current\)/, '')}</h2>
            <div className="p-months">{s.month_cover.split('').map((c, i) => <div key={i}><span>{MONTHS[i]}</span><i style={{ background: CLASS_COLOR[c as CoverClass] }} /><em>{s.calendar_months[i]}</em></div>)}</div>
            <p className="p-water">Irrigation need about <b>{afv(need.value)} acre-feet per acre</b> a year (likely {afv(need.low)}–{afv(need.high)}){s.is_baseline ? '' : `, against ${afv(needB.value)} for what the field grows now`}. {upper ? ' An upper bound: soil water stored over winter is not counted, so a dry-farmed or one-irrigation crop can need much less.' : ''} Your limit is {p.allocation.toFixed(1)}{limitWord}: <b className={over ? 'st bad' : within ? 'st good' : 'st warn'}>{over ? 'over the limit' : within ? 'fits' : 'may go over'}</b>.{cite(need.source)} In a dry year like 2022: {afv(s.exposure.replay['2022']?.irrigation_need_mm.value)}; a wet year like 2023: {afv(s.exposure.replay['2023']?.irrigation_need_mm.value)}.</p>
          </section>

          {tr && (
            <div className="p-cols">
              <section><h2>4. What it gains over today</h2><ul className="p-list gain">{tr.gains.map((g) => <li key={g}>{g}</li>)}{!tr.gains.length && <li>Nothing clearly better.</li>}</ul></section>
              <section><h2>What it gives up</h2><ul className="p-list loss">{tr.losses.map((g) => <li key={g}>{g}</li>)}{!tr.losses.length && <li>Nothing clearly worse.</li>}</ul>
                {tr.unclear.length > 0 && <p className="p-note">Too close to call: {tr.unclear.join(', ')}.</p>}</section>
            </div>
          )}

          <section>
            <h2>{tr ? '5' : '4'}. All four rotations at a glance <small>typical year</small></h2>
            <table className="p-table">
              <thead><tr><th>Rotation</th><th>Irrigation need, acre-ft/acre</th><th>Against the limit</th><th>Bare days a year</th><th>Hot bare days (104 °F)</th></tr></thead>
              <tbody>{strategies.map((x) => { const nd = x.water.irrigation_need_mm, bd = ctx.bare[x.id]?.v ?? x.exposure.bare_days_per_year.value, hb = ctx.heat[x.id]?.v; const ov = mmToAfac(nd.low ?? nd.value) > p.allocation, ok = mmToAfac(nd.high ?? nd.value) <= p.allocation; return (
                <tr key={x.id} className={x.id === s.id ? 'pick' : ''}><th>{x.short_name}{x.is_baseline ? ' (today)' : ''}</th><td>{afv(nd.value)} ({afv(nd.low)}–{afv(nd.high)}){/safflower|wheat/i.test(x.name) ? '*' : ''}</td><td>{ov ? 'over' : ok ? 'fits' : 'may go over'}</td><td>{Math.round(bd)}{x.is_baseline && ctx.bare[x.id] ? ' seen' : ' est.'}</td><td>{hb != null ? hb.toFixed(1) : '–'}</td></tr>); })}</tbody>
            </table>
            <p className="p-note">Seen = satellite record for this field; est. = rotation model. * Upper bound: stored soil water not counted.</p>
          </section>

          <section>
            <h2>{tr ? '6' : '5'}. Check locally before anything is seeded</h2>
            <ul className="p-review">
              {checks.map((c) => <li key={c.constraint}><label><input type="checkbox" /><span>{plain(c.detail)}</span></label></li>)}
              {review.map((r) => <li key={r.item}><label><input type="checkbox" checked={!!ticks[r.item]} onChange={(e) => setTicks({ ...ticks, [r.item]: e.target.checked })} /><span>{plain(r.item)}</span></label>{r.severity === 'high' && <em className="sev high">important</em>}</li>)}
              <li><label><input type="checkbox" /><span>{isBC(loc) ? 'This year’s licence volume and any fish-protection or streamflow notices on the Salmon River.' : 'This year’s water allocation or pumping limit, and any district rules on winter flooding or fallowing.'}</span></label></li>
              <li><label><input type="checkbox" /><span>Seed, buyer and price for the new crop: dollars are not counted in this summary.</span></label></li>
            </ul>
          </section>

          <footer className="p-foot">
            <div className="p-sources"><b>Sources</b>
              {sources.map((src, i) => <span key={src.id}>{i + 1}. {src.title ?? src.id}{src.verified ? '' : ' (unverified)'}</span>)}
              <span>NASA: Landsat (NASA/USGS) and Sentinel-2 (ESA) via HLS for the field calendar; NASA POWER for crop water use; NASADEM for slope. Crops: AAFC Annual Crop Inventory. Outlooks: NOAA Climate Prediction Center. Soil: BC / SoilGrids (illustrative on this outline). {BARE_DEF} {HEAT_NOTE}</span>
            </div>
            <div className="p-disclaimer">This summary supports a conversation between grower and adviser; it does not replace one.</div>
            <div>CropLytics, made for the NASA Space Apps challenge “Field Shift: Adapting Farms with NASA Data”.</div>
          </footer>
        </article>
      </div>

      <aside className="brief-rail glass">
        <div className="br-head"><h2>Summary for your adviser</h2><button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button></div>
        <Workflow current="brief" hideSteps />
        <p className="muted">Step 5: one page, Letter size. <Src p={p.prov.strategies} /></p>
        <label className="br-field"><span>Option to print</span>
          <select value={s.id} onChange={(e) => p.setPick(e.target.value)} data-testid="brief-pick">{strategies.map((x) => <option key={x.id} value={x.id}>{x.short_name}{x.is_baseline ? ' (today)' : ''}</option>)}</select>
        </label>
        <p className="muted">Sentences are fixed templates filled with the model’s numbers, each with a source.</p>
        <button className="btn primary wide" onClick={() => window.print()}><Icon name="brief" size={16} />Print or save as PDF</button>
      </aside>
    </div>
  );
}
