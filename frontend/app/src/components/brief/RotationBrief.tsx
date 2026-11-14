// Printable rotation brief (brought in from variant C, restyled for the Earth explorer, fed from the strategy data).
import { useState } from 'react';
import type { CoverClass, Location, RotationStrategy, ScoreKey, SourcedNumber, Source } from '../../types';
import type { ProvMap } from '../../api';
import { CLASS_COLOR, MONTHS, afacToMm, haToAc, mmToAfac } from '../../lib';
import Icon from '../Icons';
import { Src, fieldCode, fieldName, acres, county } from '../ui/shared';

const ROWS: [ScoreKey, string][] = [['water_use', 'Water use'], ['forage_value', 'Forage value'], ['n_fixation', 'Nitrogen fixing'], ['erosion', 'Erosion reduction'], ['organic_matter', 'Organic matter'], ['market', 'Market fit'], ['pest_break', 'Pest-cycle break'], ['infiltration', 'Infiltration'], ['n_scavenging', 'N scavenging']];
const SECTIONS = [['calendar', 'Cycle calendar'], ['why', 'Why / what the numbers say'], ['benefits', 'Benefits by priority'], ['funding', 'Funding and insurance'], ['checks', 'Fit checks'], ['review', 'Needs local review'], ['gaps', 'Gaps in the data']] as const;
type Sec = (typeof SECTIONS)[number][0];
const f0 = (v: number | null | undefined) => (v == null ? '—' : Math.round(v).toLocaleString());
const f1 = (v: number | null | undefined) => (v == null ? '—' : v.toFixed(1));
const rngTxt = (n: SourcedNumber, f = f0) => (n.low != null && n.high != null && n.low !== n.high ? `${f(n.low)}–${f(n.high)}` : f(n.value));

export default function RotationBrief({ loc, strategies, pick, setPick, allocation, prov, onClose }: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; allocation: number; prov: ProvMap; onClose: () => void }) {
  const s = strategies.find((x) => x.id === pick) ?? strategies.find((x) => !x.is_baseline) ?? strategies[0];
  const base = strategies.find((x) => x.is_baseline) ?? strategies[0];
  const [on, setOn] = useState<Record<Sec, boolean>>({ calendar: true, why: true, benefits: true, funding: true, checks: true, review: true, gaps: true });
  const [ticks, setTicks] = useState<Record<string, boolean>>({});

  if (!s) return null;
  // number sources by first use, in render order (C is called inline, not as a component, so the footer sees the full list)
  const sources: Source[] = [];
  const C = ({ n }: { n?: SourcedNumber | { source?: Source } }) => {
    const src = n?.source;
    if (!src?.id || src.id === 'mock') return null;
    let i = sources.findIndex((x) => x.id === src.id);
    if (i < 0) { sources.push(src); i = sources.length - 1; }
    return <sup className="cite" title={src.title}>{i + 1}</sup>;
  };

  const need = s.water.irrigation_need_mm, needB = base.water.irrigation_need_mm, allocMm = afacToMm(allocation);
  const over = (need.low ?? need.value) > allocMm, within = (need.high ?? need.value) <= allocMm;
  const comp = s.composite as SourcedNumber & { rank?: number; ties_with?: string[]; tie_note?: string };
  const ties = (comp.ties_with ?? []).map((id) => strategies.find((x) => x.id === id)?.short_name).filter(Boolean);
  const rain = s.exposure.exposed_rain_days, heat = s.exposure.exposed_heat_days;
  const why = s.brief.why.length ? s.brief.why.map((w) => ({ text: w.text, author: w.author, n: undefined as SourcedNumber | undefined }))
    : [
        { text: `Modelled irrigation need is ${rngTxt(need)} mm a year (${f1(mmToAfac(need.low ?? need.value))}–${f1(mmToAfac(need.high ?? need.value))} acre-ft/acre)${s.is_baseline ? '' : `, against ${rngTxt(needB)} mm for what the field grows now`}.`, n: need },
        { text: `The ground is bare about ${rngTxt(s.exposure.bare_days_per_year)} days a year${s.is_baseline ? '' : ` (now ${rngTxt(base.exposure.bare_days_per_year)})`}.`, n: s.exposure.bare_days_per_year },
        { text: `Bare or thin cover meets heavy rain on ${rngTxt(rain, f1)} days and heat on ${rngTxt(heat, f1)} days in a typical year of the 2015–2025 weather record.`, n: rain },
        { text: `With equal weight on the six priorities it scores ${f1(comp.value)} (range ${f1(comp.low)}–${f1(comp.high)})${comp.rank ? `, rank ${comp.rank} of ${strategies.length}` : ''}${ties.length ? `; a tie within uncertainty with ${ties.join(', ')}` : ''}.`, n: comp },
      ].map((w) => ({ ...w, author: 'template' }));
  const gaps = (s.brief.gaps ?? []).map((g) => (typeof g === 'string' ? g : g.text));
  const blockedFund = s.funding.length && s.funding[0].rate_per_acre_usd?.blocked;
  const rp = s.risk_profile;

  return (
    <div className="briefwrap" role="dialog" aria-label="Rotation brief" data-testid="brief">
      <div className="brief-stage">
        <article className="paper">
          <header className="p-head">
            <div>
              <div className="p-kicker">Rotation summary for {fieldName(loc)}, {county(loc)} County, California · {acres(loc)} acres · {fieldCode(loc).replace('DWR ', 'state field no. ')}</div>
              <h1>{s.name}</h1>
              <div className="p-sub">{loc.area_ha.value.toFixed(1)} ha ({haToAc(loc.area_ha.value).toFixed(0)} ac) · {loc.soil.muname}, hydrologic group {loc.soil.hydrologic_group} · prepared 14 Nov 2026</div>
            </div>
            <div className="p-score"><b>{f1(comp.value)}</b><span>fit {f1(comp.low)}–{f1(comp.high)} / 100</span>{comp.rank && <span>rank {comp.rank} of {strategies.length}</span>}{ties.length > 0 && <em>tie within uncertainty</em>}</div>
          </header>

          {on.calendar && (
            <section>
              <h2>Cycle calendar <small>{s.cycle_years > 1 ? `year ${s.strip_year ?? 1} of ${s.cycle_years}` : 'every year'}</small></h2>
              <div className="p-months">{s.month_cover.split('').map((c, i) => <div key={i}><span>{MONTHS[i]}</span><i style={{ background: CLASS_COLOR[c as CoverClass] }} /><em>{s.calendar_months[i]}</em></div>)}</div>
            </section>
          )}

          <div className="p-headline">
            <div><label>Irrigation need</label><b>{f1(mmToAfac(need.low ?? need.value))}–{f1(mmToAfac(need.high ?? need.value))} acre-ft/acre</b><span>{rngTxt(need)} mm · <i className={over ? 'st bad' : within ? 'st good' : 'st warn'}>{over ? 'over' : within ? 'within' : 'may exceed'}</i> your {allocation.toFixed(1)} acre-ft/acre{C({ n: need })}</span></div>
            <div><label>Bare days</label><b>{rngTxt(s.exposure.bare_days_per_year)} per year</b><span>today: {rngTxt(base.exposure.bare_days_per_year)}{C({ n: s.exposure.bare_days_per_year })}</span></div>
            <div><label>Exposed heavy-rain days</label><b>{rngTxt(rain, f1)} per year</b><span>today: {rngTxt(base.exposure.exposed_rain_days, f1)}{C({ n: rain })}</span></div>
            <div><label>OpenET check</label><b>{s.water.etc_vs_openet_pct ? `within ${Math.abs(s.water.etc_vs_openet_pct.value)}%` : 'not available'}</b><span>{s.water.etc_vs_openet_pct ? 'measured ET vs our model' : 'needs an OpenET key'}</span></div>
          </div>

          <div className="p-cols">
            <div>
              {on.why && (
                <section>
                  <h2>Why this rotation</h2>
                  <ul className="p-sents">{why.map((w, i) => <li key={i}>{w.text}{C({ n: w.n })}{w.author === 'template' && <span className="tmpl" title="Written from a fixed template using the engine's numbers, not by a language model">template</span>}</li>)}</ul>
                </section>
              )}
              {on.funding && (
                <section className="p-box">
                  <h2>Funding and insurance</h2>
                  {s.funding.length ? <p>Cover crops may qualify for <b>USDA EQIP practice 340</b>. {blockedFund ? <>The California payment rate is <b>not yet transcribed</b>; ask the local NRCS office.</> : null}{C({ n: s.funding[0].rate_per_acre_usd })}</p>
                    : <p>No cover-crop practice in this rotation, so EQIP 340 does not apply.</p>}
                  <p>{rp.blocked ? <>Crop-insurance loss history (USDA RMA cause of loss) is <b>not processed yet</b>.</> : <>Insurance payouts by cause: drought {Math.round(rp.rma_share_drought.value * 100)}%, excess moisture {Math.round(rp.rma_share_excess_moisture.value * 100)}%, heat {Math.round(rp.rma_share_heat.value * 100)}%.</>}{C({ n: rp.rma_share_drought })} History, not a forecast.</p>
                </section>
              )}
            </div>
            <div>
              {on.benefits && (
                <section>
                  <h2>Benefits by priority <small>range · <i className="basekey" /> today</small></h2>
                  <div className="p-ben">
                    {ROWS.map(([k, label]) => { const n = s.scores[k], b = base.scores[k]; if (!n) return null; return (
                      <div key={k}><span>{label}</span>
                        <div className="p-rb"><i style={{ left: `${n.low ?? n.value}%`, width: `${Math.max(1.5, (n.high ?? n.value) - (n.low ?? n.value))}%` }} className={n.value >= (b?.value ?? 0) ? 'g' : 'a'} />{!s.is_baseline && b && <em style={{ left: `${b.value}%` }} />}</div>
                        <b>{f0(n.value)}</b></div>); })}
                  </div>
                  <p className="p-note">Scores are rules of thumb from the engine (0–100), each a range.{C({ n: comp })}</p>
                </section>
              )}
              {on.checks && (s.constraints_check?.length ?? 0) > 0 && (
                <section>
                  <h2>Fit checks</h2>
                  <ul className="p-checks">{s.constraints_check!.map((c, i) => <li key={i}><em className={c.status === 'ok' ? 'ok' : 'no'}>{c.status}</em>{c.detail}{C({ n: c })}</li>)}</ul>
                </section>
              )}
            </div>
          </div>

          <div className="p-bottom">
            {on.review && (
              <section>
                <h2>Needs local review before anything is seeded</h2>
                <ul className="p-review">{s.brief.local_review.map((r) => (
                  <li key={r.item}><label><input type="checkbox" checked={!!ticks[r.item]} onChange={(e) => setTicks({ ...ticks, [r.item]: e.target.checked })} /><span>{r.item}</span></label><em className={`sev ${r.severity}`}>{r.severity}</em></li>
                ))}</ul>
              </section>
            )}
            {on.gaps && gaps.length > 0 && <section><h2>Gaps in the data</h2><ul className="p-gaps">{gaps.map((g) => <li key={g}>{g}</li>)}</ul></section>}
          </div>

          <footer className="p-foot">
            <div className="p-sources"><b>Sources</b>{sources.map((src, i) => <span key={src.id}>{i + 1}. {src.title ?? src.id}{src.verified ? '' : ' (unverified)'}</span>)}</div>
            <div className="p-disclaimer">This brief supports a conversation between grower and adviser; it does not replace one. Every alternative rotation needs review by both before anything is seeded.</div>
          </footer>
        </article>
      </div>

      <aside className="brief-rail glass">
        <div className="br-head"><h2>Rotation brief</h2><button className="sq-btn" onClick={onClose} title="Close"><Icon name="close" size={16} /></button></div>
        <p className="muted">One sheet, Letter or A4 portrait. <Src p={prov.strategies} /></p>
        <label className="br-field"><span>Rotation</span>
          <select value={s.id} onChange={(e) => setPick(e.target.value)} data-testid="brief-pick">{strategies.map((x) => <option key={x.id} value={x.id}>{x.short_name}{x.is_baseline ? ' (today)' : ''}</option>)}</select>
        </label>
        <div className="br-field"><span>Sections</span>
          {SECTIONS.map(([id, label]) => <label key={id} className="chk"><input type="checkbox" checked={on[id]} onChange={(e) => setOn({ ...on, [id]: e.target.checked })} />{label}</label>)}
        </div>
        <div className="br-field"><span>Text check</span>
          <p className="muted">{s.brief.llm_report ? `${s.brief.llm_report.sentences} sentences, ${s.brief.llm_report.numbers_checked} numbers checked, ${s.brief.llm_report.rejected} rejected.` : 'No AI text yet: sentences are fixed templates filled with the engine’s numbers, each cited.'}</p>
        </div>
        <div className="br-field"><span>Sources · {sources.filter((x) => x.verified).length} of {sources.length} verified</span>
          <ol className="br-src">{sources.map((src) => <li key={src.id} className={src.verified ? 'v' : 'u'}>{src.url && /^https?:/.test(src.url) ? <a href={src.url} target="_blank" rel="noreferrer">{src.title ?? src.id}</a> : (src.title ?? src.id)}</li>)}</ol>
        </div>
        <button className="btn primary wide" onClick={() => window.print()}><Icon name="brief" size={16} />Print or save as PDF</button>
      </aside>
    </div>
  );
}
