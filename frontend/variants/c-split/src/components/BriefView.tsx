import { useMemo, useState } from 'react';
import { MM_PER_AF_AC, PRIORITIES, getSource, haToAc, mmToAfAc } from '../api';
import type { BriefSentence, Location, ScoreKey, ScoredStrategy } from '../types';
import { ALLOC_TEXT, COVER_LABEL, Icon, MONTH_NAMES, ScoreRange, allocStatus, fmt, fmtRange, rng } from './Bits';

const ROWS: { key: ScoreKey; label: string }[] = [...PRIORITIES.map((p) => ({ key: p.key as ScoreKey, label: p.label })), { key: 'pest_break', label: 'Pest-cycle break' }, { key: 'infiltration', label: 'Infiltration' }, { key: 'n_scavenging', label: 'N scavenging' }];
const SECTIONS = [
  { id: 'calendar', label: 'Cycle calendar' }, { id: 'why', label: 'Why this rotation' }, { id: 'evidence', label: 'Evidence' }, { id: 'benefits', label: 'Benefits by priority' },
  { id: 'funding', label: 'Funding and income' }, { id: 'insurance', label: 'Insurance history' }, { id: 'review', label: 'Needs local review' }, { id: 'gaps', label: 'Gaps in the data' },
] as const;
type SectionId = (typeof SECTIONS)[number]['id'];

export default function BriefView({ loc, items, id, allocation, onPick, onClose }: { loc: Location; items: ScoredStrategy[]; id: string; allocation: number; onPick: (id: string) => void; onClose: () => void }) {
  const s = items.find((x) => x.id === id)!;
  const base = items.find((x) => x.is_baseline)!;
  const [on, setOn] = useState<Record<SectionId, boolean>>({ calendar: true, why: true, evidence: true, benefits: true, funding: true, insurance: true, review: true, gaps: true });
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  const allocMm = allocation * MM_PER_AF_AC;
  const need = rng(s.water.irrigation_need_mm);
  const st = allocStatus(need, allocMm);
  // number the sources in order of first use
  const srcIds = useMemo(() => {
    const ids: string[] = [];
    const add = (i: string) => { if (!ids.includes(i) && getSource(i)) ids.push(i); };
    [...s.brief.why, ...s.brief.evidence].forEach((b) => b.source_ids.forEach(add));
    [s.month_strip_source, 'rma_col', ...(s.funding.length ? ['nrcs_eqip'] : [])].forEach(add);
    return ids.filter((i) => i !== 'mock');
  }, [s]);
  const Sent = ({ b }: { b: BriefSentence }) => (
    <>
      {b.text}{' '}
      {b.source_ids.filter((i) => srcIds.includes(i)).map((i) => {
        const src = getSource(i);
        return <a key={i} className={`cite${src.verified ? '' : ' unv'}`} href={src.url ?? undefined} target="_blank" rel="noreferrer" title={src.title}><b>{srcIds.indexOf(i) + 1}</b>{src.short ?? src.title}</a>;
      })}
      {b.author === 'template' && <span className="tmpl" title="Written from a fixed template, not by the language model">template</span>}
    </>
  );
  const rma = s.risk_profile;
  return (
    <div className="briefwrap" role="dialog" aria-label="Rotation brief">
      <div className="brief-stage">
        <div className="paper" id="paper">
          <header className="p-head">
            <div>
              <div className="p-kicker">Rotation brief · {loc.short_name}</div>
              <h1>{s.name}</h1>
              <div className="p-sub">{loc.region_label} · {fmt(loc.area_ha.value)} ha ({fmt(haToAc(loc.area_ha.value))} acres) · {loc.soil.texture_class.toLowerCase()}, {loc.soil.drainage_class.toLowerCase()} · prepared 14 Nov 2026</div>
            </div>
            <div className="p-score">
              <b>{s.composite.value}</b><span>fit {s.composite.low}–{s.composite.high} / 100</span>
              {s.tie && <em>tie within uncertainty</em>}
            </div>
          </header>
          <div className="p-mock">Prototype: numbers are illustrative mock data. Dates, events and links are real.</div>

          {on.calendar && (
            <section className="p-cal">
              <h2>Cycle calendar{s.year_shown ? ` (${s.year_shown})` : ''}</h2>
              <div className="p-months">
                {s.month_strip.map((m, i) => (
                  <div key={i}><span>{MONTH_NAMES[i]}</span><i className={`cov-${m.state}`} title={COVER_LABEL[m.state]} /><em>{m.label}</em></div>
                ))}
              </div>
            </section>
          )}

          <div className="p-headline">
            <div><label>Irrigation need</label><b>{fmtRange(mmToAfAc(need.low), mmToAfAc(need.high), 1)} acre-ft/acre</b><span>{fmtRange(need.low, need.high)} mm · <i className={`st st-${st}`}>{ALLOC_TEXT[st].toLowerCase()}</i> ({fmt(allocation, 1)})</span></div>
            <div><label>Exposed heavy-rain days</label><b>{fmtRange(s.exposure.exposed_rain_days.low!, s.exposure.exposed_rain_days.high!)} per year</b><span>today: {fmtRange(base.exposure.exposed_rain_days.low!, base.exposure.exposed_rain_days.high!)}</span></div>
            <div><label>Bare days</label><b>{fmtRange(s.exposure.bare_days_per_year.low!, s.exposure.bare_days_per_year.high!)} per year</b><span>today: {fmtRange(base.exposure.bare_days_per_year.low!, base.exposure.bare_days_per_year.high!)}</span></div>
            <div><label>OpenET check</label><b>{s.water.etc_vs_openet_pct ? `within ${Math.abs(s.water.etc_vs_openet_pct.value)}%` : 'not available'}</b><span>measured ET vs our model</span></div>
          </div>

          <div className="p-cols">
            <div>
              {on.why && (<section><h2>Why this rotation</h2><ul className="p-sents">{s.brief.why.map((b, i) => <li key={i}><Sent b={b} /></li>)}</ul></section>)}
              {on.evidence && (<section><h2>Evidence from the data</h2><ul className="p-sents dots">{s.brief.evidence.map((b, i) => <li key={i}><Sent b={b} /></li>)}</ul></section>)}
            </div>
            <div>
              {on.benefits && (
                <section>
                  <h2>Benefits by priority <small>range · <i className="basekey" /> today</small></h2>
                  <div className="p-ben">
                    {ROWS.map((r) => (
                      <div key={r.key}><span>{r.label}</span><ScoreRange r={rng(s.scores[r.key])} tone={s.scores[r.key].value >= base.scores[r.key].value ? 'green' : 'amber'} baseline={s.is_baseline ? undefined : base.scores[r.key].value} /><b>{s.scores[r.key].value}</b></div>
                    ))}
                  </div>
                </section>
              )}
              {on.funding && (
                <section className="p-box">
                  <h2>Funding and income</h2>
                  {s.funding.length > 0
                    ? <p>Cover crops may qualify for <b>USDA EQIP practice 340</b>. The payment rate is a range set by the state schedule; <b>rate not yet confirmed</b> for this county; ask the local NRCS office. <a className="cite unv" href={s.funding[0].url} target="_blank" rel="noreferrer"><b>{srcIds.indexOf('nrcs_eqip') + 1}</b>NRCS EQIP</a></p>
                    : <p>No cover-crop practice in this rotation, so EQIP 340 does not apply. Income depends on local prices: always a range, confirm locally.</p>}
                </section>
              )}
              {on.insurance && (
                <section>
                  <h2>Insurance history <small>{rma.rma_years[0]}–{rma.rma_years[1]}</small></h2>
                  <div className="rmabar tall"><i className="rma-drought" style={{ width: `${rma.rma_share_drought.value}%` }}>Drought {rma.rma_share_drought.value}%</i><i className="rma-wet" style={{ width: `${rma.rma_share_excess_moisture.value}%` }}>Too wet {rma.rma_share_excess_moisture.value}%</i><i className="rma-heat" style={{ width: `${rma.rma_share_heat.value}%` }} /><i className="rma-other" style={{ width: `${rma.rma_share_other.value}%` }}>Other</i></div>
                  <p className="p-note">{rma.rma_label}: share of crop-insurance payouts by cause. Insurance history, not a forecast. <a className="cite unv" href={getSource('rma_col').url!} target="_blank" rel="noreferrer"><b>{srcIds.indexOf('rma_col') + 1}</b>USDA RMA</a></p>
                </section>
              )}
              {on.gaps && (<section><h2>Gaps in the data</h2><ul className="p-gaps">{s.brief.gaps.map((g) => <li key={g}>{g}</li>)}</ul></section>)}
            </div>
          </div>

          {on.review && (
            <section className="p-reviewsec">
                  <h2>Needs local review before anything is seeded</h2>
                  <ul className="p-review">
                    {s.brief.local_review.map((r) => (
                      <li key={r.item}>
                        <label><input type="checkbox" checked={!!ticks[r.item]} onChange={(e) => setTicks({ ...ticks, [r.item]: e.target.checked })} /><span>{r.item}</span></label>
                        <em className={`sev sev-${r.severity}`}>{r.severity}</em>
                      </li>
                    ))}
                  </ul>
            </section>
          )}

          <footer className="p-foot">
            <div className="p-sources">
              <b>Sources</b>
              {srcIds.map((i, n) => { const src = getSource(i); return <span key={i}>{n + 1}. {src.title}{!src.verified && ' (unverified)'}</span>; })}
            </div>
            <div className="p-ai"><Icon name="check" size={13} />AI text check: {s.brief.llm_report.sentences} sentences, {s.brief.llm_report.numbers_checked} numbers checked against the data, {s.brief.llm_report.rejected} rejected and replaced by a template.</div>
            <div className="p-disclaimer">This brief supports a conversation between grower and adviser; it does not replace one. Every alternative rotation needs review by the grower and an adviser before anything is seeded.</div>
          </footer>
        </div>
      </div>

      <aside className="brief-rail">
        <div className="rail-head"><h2>Print brief</h2><button className="iconbtn" onClick={onClose} aria-label="Close brief" data-action="close-brief"><Icon name="close" /></button></div>
        <div className="rail-total">1 sheet · A4 portrait</div>
        <label className="rail-field"><span>Rotation</span>
          <select value={id} onChange={(e) => onPick(e.target.value)}>{items.map((x) => <option key={x.id} value={x.id}>{x.short}{x.is_baseline ? ' (today)' : ''}</option>)}</select>
        </label>
        <div className="rail-field"><span>Sections</span>
          <div className="rail-secs">
            {SECTIONS.map((sec) => <label key={sec.id} className="chk"><input type="checkbox" checked={on[sec.id]} onChange={(e) => setOn({ ...on, [sec.id]: e.target.checked })} />{sec.label}</label>)}
          </div>
        </div>
        <div className="rail-check">
          <h3><Icon name="check" size={15} />Every sentence is checked</h3>
          <div className="rail-stats">
            <div><b>{s.brief.llm_report.sentences}</b><span>sentences</span></div>
            <div><b>{s.brief.llm_report.numbers_checked}</b><span>numbers matched to data</span></div>
            <div><b>{s.brief.llm_report.rejected}</b><span>rejected, replaced</span></div>
          </div>
          <p>A sentence with a number that is not in the data is thrown out and replaced by a fixed template.</p>
        </div>
        <div className="rail-field"><span>Sources on this page · {srcIds.filter((i) => getSource(i).verified).length} of {srcIds.length} verified</span>
          <ol className="rail-src">
            {srcIds.map((i) => { const src = getSource(i); return <li key={i} className={src.verified ? 'v' : 'u'}>{src.url ? <a href={src.url} target="_blank" rel="noreferrer">{src.short ?? src.title}</a> : src.short}<em>{src.verified ? 'verified' : 'to verify'}</em></li>; })}
          </ol>
        </div>
        <div className="rail-actions">
          <button className="btn primary wide" onClick={() => window.print()}><Icon name="print" size={16} />Print or save as PDF</button>
          <button className="btn outline wide" onClick={onClose}>Back to compare</button>
        </div>
      </aside>
    </div>
  );
}
