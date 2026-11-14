import { useState } from 'react';
import type { CoverClass, Location, RotationStrategy, ScoreKey, SourcedNumber } from '../types';
import { CLASS_COLOR, afacToMm, mmToAfac, mmToIn, overlapShare } from '../lib';
import Icon from './Icons';

const SCORES: [ScoreKey, string, boolean][] = [
  ['water_use', 'Water use', true], ['forage_value', 'Forage value', true], ['n_fixation', 'Nitrogen fixing', true], ['erosion', 'Erosion reduction', true], ['organic_matter', 'Organic matter', true], ['market', 'Market fit', true],
  ['pest_break', 'Pest-cycle break', false], ['infiltration', 'Infiltration', false], ['n_scavenging', 'Nitrogen scavenging', false],
];
const pct = (v: number, max = 100) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;

function RangeBar({ n, max = 100, color, mark }: { n: SourcedNumber; max?: number; color: string; mark?: number }) {
  const lo = n.low ?? n.value, hi = n.high ?? n.value;
  return (
    <div className="rb" title={`${n.value} (range ${lo}–${hi}) ${n.unit}`}>
      <div className="rb-range" style={{ left: pct(lo, max), width: `calc(${pct(hi - lo, max)} + 2px)`, background: color }} />
      <div className="rb-whisk" style={{ left: pct(lo, max) }} /><div className="rb-whisk" style={{ left: pct(hi, max) }} />
      <div className="rb-val" style={{ left: pct(n.value, max) }} />
      {mark != null && <div className="rb-mark" style={{ left: pct(mark, max) }} />}
    </div>
  );
}

export default function ComparePanel(p: { loc: Location; strategies: RotationStrategy[]; allocation: number; setAllocation: (v: number) => void; onBrief: (id: string) => void; onClose: () => void }) {
  const [replay, setReplay] = useState<'typical' | '2022' | '2023'>('typical');
  const [more, setMore] = useState(true);
  const best = [...p.strategies].sort((a, b) => b.composite.value - a.composite.value)[0];
  const allocMm = afacToMm(p.allocation);
  const IMAX = 1700;
  return (
    <section className="compare glass" data-testid="compare">
      <header className="cmp-head">
        <div className="cmp-title">
          <h2>Compare rotations</h2>
          <span>{p.loc.short_name} · current rotation and three alternatives · every score is a range</span>
        </div>
        <div className="cmp-alloc">
          <label>Water you expect <b>{p.allocation.toFixed(1)} acre-ft/acre</b> <small>({Math.round(allocMm)} mm · {mmToIn(allocMm).toFixed(0)} in)</small></label>
          <input type="range" min={0.5} max={5} step={0.1} value={p.allocation} onChange={(e) => p.setAllocation(+e.target.value)} data-testid="alloc" />
        </div>
        <div className="seg">
          <button className={replay === 'typical' ? 'on' : ''} onClick={() => setReplay('typical')}>Typical year</button>
          <button className={replay === '2022' ? 'on' : ''} onClick={() => setReplay('2022')} data-testid="replay-2022">Replay 2022 <i>drought</i></button>
          <button className={replay === '2023' ? 'on' : ''} onClick={() => setReplay('2023')}>Replay 2023 <i>flood</i></button>
        </div>
        <button className="icon-btn" onClick={p.onClose} title="Close"><Icon name="close" /></button>
      </header>
      <div className="cmp-cols">
        {p.strategies.map((s, i) => {
          const ov = overlapShare(s.composite, best.composite);
          const isBest = s.id === best.id;
          const irr = replay === 'typical' ? s.water.irrigation_need_mm : s.exposure.replay[replay].irrigation_need_mm;
          const rain = replay === 'typical' ? s.exposure.exposed_rain_days : s.exposure.replay[replay].exposed_rain_days;
          const over = (irr.low ?? irr.value) > allocMm, within = (irr.high ?? irr.value) <= allocMm;
          return (
            <article key={s.id} className={`cmp-col ${s.is_baseline ? 'base' : ''}`}>
              <div className="cmp-kicker">
                <span className={`chip ${s.is_baseline ? 'neutral' : 'accent'}`}>{s.is_baseline ? 'What you do now' : `Alternative ${i}`}</span>
                {isBest ? <span className="chip good">Highest score</span> : ov > 0.5 ? <span className="chip tie" title={`Ranges overlap by ${Math.round(ov * 100)}% with the top option`}>Tie within uncertainty</span> : <span className="chip neutral">Behind top option</span>}
              </div>
              <h3>{s.name}</h3>
              <div className="month-strip" title="Month-by-month ground cover in a typical cycle year">
                {s.month_cover.split('').map((c, m) => <i key={m} title={s.calendar_months[m]} style={{ background: CLASS_COLOR[c as CoverClass] }}>{'JFMAMJJASOND'[m]}</i>)}
              </div>
              <div className="cmp-block">
                <div className="cmp-row-head"><span>Overall, with your priorities</span><b>{s.composite.value}<small> ({s.composite.low}–{s.composite.high})</small></b></div>
                <RangeBar n={s.composite} color="var(--accent)" />
              </div>
              <div className="cmp-block water">
                <div className="cmp-row-head"><span>Irrigation need{replay !== 'typical' ? ` · ${replay}` : ''}</span><b>{irr.value.toLocaleString()} mm<small> ({mmToAfac(irr.value).toFixed(1)} acre-ft/acre)</small></b></div>
                <RangeBar n={irr} max={IMAX} color={over ? '#ff7a6b' : within ? '#55c5f0' : '#f2c14e'} mark={allocMm} />
                <div className="cmp-alloc-line">
                  <span className={`chip ${over ? 'bad' : within ? 'good' : 'tie'}`}>{over ? 'Over your allocation' : within ? 'Within your allocation' : 'May exceed allocation'}</span>
                  <small>range {irr.low?.toLocaleString()}–{irr.high?.toLocaleString()} mm ({mmToIn(irr.low ?? 0).toFixed(0)}–{mmToIn(irr.high ?? 0).toFixed(0)} in)</small>
                </div>
                {replay !== 'typical' && <p className="replay-note">{s.exposure.replay[replay].note}</p>}
              </div>
              <div className="cmp-scores">
                {SCORES.filter(([, , main]) => main || more).map(([k, label, main]) => (
                  <div key={k} className={`score ${main ? '' : 'extra'}`}>
                    <span>{label}</span>
                    <RangeBar n={s.scores[k]} color={main ? '#8ab4f8' : '#9aa6b8'} />
                    <em>{s.scores[k].value}</em>
                  </div>
                ))}
              </div>
              <div className="cmp-chips">
                <span className="chip neutral" title={`Days per year the field is bare during heavy rain (${s.exposure.cover_basis})`}><Icon name="drop" size={12} />{rain.value} exposed heavy-rain days <small>({rain.low}–{rain.high})</small></span>
                <span className="chip neutral">{s.exposure.bare_days_per_year.value} bare days/yr</span>
                {s.water.etc_vs_openet_pct && <span className="chip good" title="Modelled crop water use vs OpenET measured ET, baseline crop"><Icon name="check" size={12} />OpenET check {s.water.etc_vs_openet_pct.value > 0 ? '+' : ''}{s.water.etc_vs_openet_pct.value}%</span>}
              </div>
              <div className="rma" title={`${s.risk_profile.crop}, ${s.risk_profile.rma_years.join('–')}: ${s.risk_profile.note}`}>
                <span>Past insured losses</span>
                <div className="rma-bar">
                  <i style={{ width: pct(s.risk_profile.rma_share_drought.value, 1), background: '#e0a04a' }} />
                  <i style={{ width: pct(s.risk_profile.rma_share_excess_moisture.value, 1), background: '#4a9be0' }} />
                  <i style={{ width: pct(s.risk_profile.rma_share_heat.value, 1), background: '#e0604a' }} />
                </div>
                <small>drought {Math.round(s.risk_profile.rma_share_drought.value * 100)}% · excess moisture {Math.round(s.risk_profile.rma_share_excess_moisture.value * 100)}% · heat {Math.round(s.risk_profile.rma_share_heat.value * 100)}%</small>
              </div>
              <button className="btn" onClick={() => p.onBrief(s.id)}>Open brief<Icon name="right" size={16} /></button>
            </article>
          );
        })}
      </div>
      <footer className="cmp-foot">
        <span><i className="key-range" />bar = low–high range, tick = best estimate</span>
        <span><i className="key-mark" />your allocation</span>
        <span>Tie = ranges overlap by more than half</span>
        <button className="link" onClick={() => setMore(!more)}>{more ? 'Hide' : 'Show'} extra factors</button>
        <span className="right">Rules of thumb, not a model. Supports, doesn’t replace, your adviser.</span>
      </footer>
    </section>
  );
}
