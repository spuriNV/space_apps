import { useState } from 'react';
import { getStrategies } from '../api';
import type { LocationId, RotationStrategy, ScoreKey, SourcedNumber } from '../types';
import { COVER_COLORS, MM_PER_AFAC, MONTH_LETTERS, fmt, mmToAfac, mmToIn } from '../util';
import Icon from './Icon';

const SCORES: { key: ScoreKey; label: string; group: 'six' | 'extra' }[] = [
  { key: 'water_use', label: 'Water use', group: 'six' },
  { key: 'forage_value', label: 'Forage value', group: 'six' },
  { key: 'n_fixation', label: 'Nitrogen fixing', group: 'six' },
  { key: 'erosion', label: 'Erosion reduction', group: 'six' },
  { key: 'organic_matter', label: 'Organic matter', group: 'six' },
  { key: 'market', label: 'Market fit', group: 'six' },
  { key: 'pest_break', label: 'Pest-cycle break', group: 'extra' },
  { key: 'infiltration', label: 'Infiltration', group: 'extra' },
  { key: 'n_scavenging', label: 'Nitrogen scavenging', group: 'extra' },
];

type Range = { value: number; low: number; high: number };
/** Tie rule (spec B4.12): intervals overlapping by more than half are a tie within uncertainty. */
function overlapShare(a: Range, b: Range) {
  const wa = a.high - a.low, wb = b.high - b.low;
  if (wa <= 0 || wb <= 0) return a.value === b.value && a.value > 0 ? 1 : 0;
  return Math.max(0, Math.min(a.high, b.high) - Math.max(a.low, b.low)) / Math.min(wa, wb);
}
function badges(ranges: Range[]): ('top' | 'tie' | null)[] {
  const best = ranges.reduce((bi, r, i) => (r.value > ranges[bi].value ? i : bi), 0);
  if (ranges[best].value <= 0) return ranges.map(() => null);
  const tied = ranges.map((r, i) => i !== best && overlapShare(r, ranges[best]) > 0.5);
  const any = tied.some(Boolean);
  return ranges.map((_, i) => (i === best ? (any ? 'tie' : 'top') : tied[i] ? 'tie' : null));
}
const rng = (s: SourcedNumber): Range => ({ value: s.value, low: s.low ?? s.value, high: s.high ?? s.value });

function RangeBar({ r, badge, color = '#1a73e8', baseline }: { r: Range; badge: 'top' | 'tie' | null; color?: string; baseline?: boolean }) {
  return (
    <div className="rb">
      <div className="rb-track">
        <span className="rb-span" style={{ left: `${r.low}%`, width: `${Math.max(1.5, r.high - r.low)}%`, background: baseline ? '#9aa0a6' : color }} />
        <span className="rb-dot" style={{ left: `${r.value}%`, borderColor: baseline ? '#5f6368' : color }} />
      </div>
      <span className="rb-num">{r.value}<small>{r.low}–{r.high}</small></span>
      <span className="rb-badge">{badge === 'tie' ? <span className="tie">Tie</span> : badge === 'top' ? <span className="top">Top</span> : null}</span>
    </div>
  );
}

export default function CompareTab({ id, allocation, onAllocation, onBrief }: { id: LocationId; allocation: number; onAllocation: (v: number) => void; onBrief: () => void }) {
  const strategies = getStrategies(id);
  const [mode, setMode] = useState<'typical' | '2022' | '2023'>('typical');
  const allocMm = allocation * MM_PER_AFAC;
  const need = (s: RotationStrategy): Range => (mode === 'typical' ? rng(s.water.irrigation_need_mm) : rng(s.exposure.replay[mode].irrigation_need_mm));
  const rain = (s: RotationStrategy): Range => (mode === 'typical' ? rng(s.exposure.exposed_rain_days) : rng(s.exposure.replay[mode].exposed_rain_days));
  const maxNeed = Math.max(1600, ...strategies.map((s) => s.water.irrigation_need_mm.high ?? 0));
  const compBadges = badges(strategies.map((s) => s.composite));
  const rma = strategies[0].risk_profile;
  const rmaParts = [
    { k: 'Drought', v: rma.rma_share_drought.value, c: '#e37400' },
    { k: 'Too much water', v: rma.rma_share_excess_moisture.value, c: '#1a73e8' },
    { k: 'Heat', v: rma.rma_share_heat.value, c: '#d93025' },
    { k: 'Other', v: rma.rma_share_other.value, c: '#9aa0a6' },
  ];

  return (
    <div className="tab-body compare-tab">
      <div className="cmp-top">
        <div>
          <div className="h2">Compare rotations</div>
          <div className="muted">Every bar is a range, not a single number. Where ranges overlap by more than half, we call it a tie.</div>
        </div>
        <div className="cmp-controls">
          <div className="seg" role="group" aria-label="Year to replay">
            <button className={mode === 'typical' ? 'on' : ''} onClick={() => setMode('typical')}>Typical year</button>
            <button className={mode === '2022' ? 'on' : ''} onClick={() => setMode('2022')}>Replay 2022 drought</button>
            <button className={mode === '2023' ? 'on' : ''} onClick={() => setMode('2023')}>Replay 2023 storms</button>
          </div>
        </div>
      </div>

      <div className="cmp-grid">
        {/* header row */}
        <div className="cmp-label cmp-alloc">
          <div className="card-k">Your water allocation</div>
          <div className="alloc-v">{fmt(allocation, 1)} <small>acre-ft/acre</small></div>
          <div className="muted">{fmt(allocMm)} mm · {fmt(mmToIn(allocMm), 1)} in</div>
          <input type="range" min={0.5} max={5} step={0.1} value={allocation} onChange={(e) => onAllocation(Number(e.target.value))} aria-label="Water allocation in acre-feet per acre" />
        </div>
        {strategies.map((s) => (
          <div className={`cmp-head${s.is_baseline ? ' is-base' : ''}`} key={s.id}>
            <span className={`cmp-tag${s.is_baseline ? ' base' : ''}`}>{s.is_baseline ? 'Current' : 'Alternative'}</span>
            <div className="cmp-name">{s.name}</div>
            <div className="cmp-line">{s.one_line}</div>
            <div className="mstrip" title={s.month_labels.map((m, i) => `${MONTH_LETTERS[i]}: ${m}`).join('\n')}>
              {s.month_cover.split('').map((c, i) => <span key={i} style={{ background: COVER_COLORS[c] }}>{MONTH_LETTERS[i]}</span>)}
            </div>
          </div>
        ))}

        <div className="cmp-label"><b>Overall</b><span>six priorities, equal weight</span></div>
        {strategies.map((s, i) => <div className={`cmp-cell strong${s.is_baseline ? ' is-base' : ''}`} key={s.id}><RangeBar r={s.composite} badge={compBadges[i]} baseline={s.is_baseline} color="#188038" /></div>)}

        <div className="cmp-label"><b>Irrigation need</b><span>against your allocation{mode !== 'typical' ? `, ${mode}` : ''}</span></div>
        {strategies.map((s) => {
          const n = need(s);
          const over = n.low > allocMm, under = n.high <= allocMm;
          return (
            <div className={`cmp-cell tall${s.is_baseline ? ' is-base' : ''}`} key={s.id}>
              <div className="need">
                <div className="need-track">
                  <span className="need-span" style={{ left: `${(n.low / maxNeed) * 100}%`, width: `${Math.max(1.5, ((n.high - n.low) / maxNeed) * 100)}%`, background: over ? '#d93025' : under ? '#188038' : '#e37400' }} />
                  <span className="need-dot" style={{ left: `${(n.value / maxNeed) * 100}%` }} />
                  <span className="need-alloc" style={{ left: `${Math.min(100, (allocMm / maxNeed) * 100)}%` }} />
                </div>
                <div className="need-text"><b>{fmt(n.value)} mm</b> · {fmt(mmToAfac(n.value), 1)} acre-ft/acre</div>
                <span className={`status ${over ? 'bad' : under ? 'good' : 'warn'}`}>{over ? 'Over allocation' : under ? 'Within allocation' : 'Close: range crosses it'}</span>
              </div>
            </div>
          );
        })}

        <div className="cmp-label"><b>Bare in heavy rain</b><span>days a year{mode !== 'typical' ? `, ${mode}` : ''}</span></div>
        {strategies.map((s) => {
          const r = rain(s);
          return (
            <div className={`cmp-cell${s.is_baseline ? ' is-base' : ''}`} key={s.id}>
              <div className="dots">{Array.from({ length: 10 }, (_, i) => <i key={i} className={i < r.value ? 'on' : i < r.high ? 'maybe' : ''} />)}</div>
              <span className="rb-num">{r.value}<small>{r.low !== r.high ? `${r.low}–${r.high}` : 'days'}</small></span>
            </div>
          );
        })}

        <div className="cmp-label"><b>Satellite check</b><span>OpenET measured vs our model</span></div>
        {strategies.map((s) => (
          <div className={`cmp-cell${s.is_baseline ? ' is-base' : ''}`} key={s.id}>
            {mode !== 'typical' ? <span className="note">{s.exposure.replay[mode].note}</span>
              : s.water.etc_vs_openet_pct ? <span className="status good"><Icon name="check" size={14} />Model {s.water.etc_vs_openet_pct.value > 0 ? '+' : ''}{s.water.etc_vs_openet_pct.value}% vs OpenET</span>
              : <span className="note">Modelled only: not grown here yet</span>}
          </div>
        ))}

        <div className="cmp-sep">Scores, 0–100 (higher is better)</div>
        {SCORES.map((sc, k) => {
          const ranges = strategies.map((s) => rng(s.scores[sc.key]));
          const b = badges(ranges);
          return [
            <div className={`cmp-label slim${k === 6 ? ' gap' : ''}`} key={sc.key}><b>{sc.label}</b></div>,
            ...strategies.map((s, i) => <div className={`cmp-cell slim${k === 6 ? ' gap' : ''}${s.is_baseline ? ' is-base' : ''}`} key={s.id + sc.key}><RangeBar r={ranges[i]} badge={b[i]} baseline={s.is_baseline} /></div>),
          ];
        })}

        <div className="cmp-label"><b>Past insured losses</b><span>{rma.crop}, {rma.rma_years.join('–')}</span></div>
        <div className="cmp-cell span4">
          <div className="rma">{rmaParts.map((p) => <span key={p.k} style={{ width: `${p.v * 100}%`, background: p.c }} />)}</div>
          <div className="rma-key">{rmaParts.map((p) => <span key={p.k}><i style={{ background: p.c }} />{p.k} {Math.round(p.v * 100)}%</span>)}<em>Insurance history, not a forecast.</em></div>
        </div>

        <div className="cmp-label" />
        {strategies.map((s) => (
          <div className={`cmp-cell foot${s.is_baseline ? ' is-base' : ''}`} key={s.id}>
            {s.is_baseline ? <span className="note">Baseline for the others</span> : <button className="pill-btn blue" onClick={onBrief}><Icon name="description" size={16} />Open brief</button>}
          </div>
        ))}
      </div>
      <div className="footnote">Alternatives use modelled cover; the current rotation uses what the satellites observed. Scores are rules of thumb with ranges. Every alternative needs review by the grower and an adviser before anything is seeded.</div>
    </div>
  );
}
