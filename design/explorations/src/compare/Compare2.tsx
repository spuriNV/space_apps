// Option 2 — pick one alternative; see what you gain and what you give up compared with what you do now.
import { useState } from 'react';
import { ALTS, DEFAULT_W, PLAIN, SHORT, TODAY, mmAf, overall, overlapShare, r0, verdict } from '../data';
import { AssumedNote, Ranges } from '../ui';
import { EXTRA_METRICS, Metric, SCORE_METRICS, UNIT_METRICS, Weather, WEATHER_LABEL, span } from './common';

function deltaText(m: Metric, alt: number, base: number) {
  const d = Math.abs(alt - base);
  if (m.key === 'water') return `about ${r0(d)} mm (${mmAf(d)}) ${alt < base ? 'less' : 'more'} a year`;
  if (m.unit === 'days/yr') return `about ${d < 10 ? d.toFixed(1) : r0(d)} ${alt < base ? 'fewer' : 'more'} days a year`;
  return `${r0(alt)} vs ${r0(base)} out of 100`;
}

export default function Compare2({ weather, pickId }: { weather: Weather; pickId?: string }) {
  const [id, setId] = useState(pickId ?? 'car2_dryyear_safflower');
  const alt = ALTS.find((s) => s.id === id)!;
  // water_use score is the irrigation-water row restated, so it is not listed twice
  const all = [...UNIT_METRICS, ...SCORE_METRICS.filter((m) => m.key !== 'water_use'), ...EXTRA_METRICS];
  const rows = all.map((m) => {
    const a = m.get(alt, weather), b = m.get(TODAY, weather);
    return { m, a, b, v: verdict(a, b, m.higherIsBetter) };
  });
  const gains = rows.filter((r) => r.v === 'better');
  const losses = rows.filter((r) => r.v === 'worse');
  const unclear = rows.filter((r) => r.v === 'unclear' || r.v === 'same');
  const none = rows.filter((r) => r.v === 'none');
  const oa = overall(alt, DEFAULT_W), ot = overall(TODAY, DEFAULT_W);
  const ties = ALTS.filter((t) => t.id !== id && overlapShare([oa.lo, oa.hi], [overall(t, DEFAULT_W).lo, overall(t, DEFAULT_W).hi]) > 0.5);
  const lead = (r: (typeof rows)[number] | undefined, k: 'gain' | 'loss') => (r ? `${r.m[k].replace(/: (better|worse)$/, '').toLowerCase()}, ${deltaText(r.m, r.a.v!, r.b.v!)}` : 'nothing clear');

  const Item = ({ r, kind }: { r: (typeof rows)[number]; kind: 'gain' | 'loss' }) => {
    const [lo1, hi1] = span(r.b), [lo2, hi2] = span(r.a);
    const max = r.m.unit === 'score' ? 100 : Math.max(hi1, hi2) * 1.1 || 1;
    return (
      <li className={`gl-item ${kind}`}>
        <div className="gl-head"><b>{kind === 'gain' ? r.m.gain : r.m.loss}</b><span>{deltaText(r.m, r.a.v!, r.b.v!)}</span></div>
        <Ranges min={0} max={max} ticks={3} height={16} unit={r.m.unit === 'score' ? '' : r.m.unit}
          items={[{ label: 'Today', lo: lo1, hi: hi1, v: r.b.v!, color: '#9aa3ad' }, { label: 'This', lo: lo2, hi: hi2, v: r.a.v!, color: kind === 'gain' ? '#7ee0a1' : '#f2a65a' }]} />
      </li>
    );
  };

  return (
    <section className="panel glass wide c2">
      <header className="ph row">
        <div>
          <h1>If you switched, what would you gain and what would you give up?</h1>
          <p className="headline">
            <b>{SHORT[id]}</b> vs what you do now: you’d gain <b className="good">{lead(gains[0], 'gain')}</b>. You’d give up <b className="bad">{lead(losses[0], 'loss')}</b>.
          </p>
        </div>
        <AssumedNote />
      </header>
      <div className="c2-tabs">
        <span className="muted">Compare today’s rice + winter flood with</span>
        {ALTS.map((s) => (
          <button key={s.id} className={s.id === id ? 'on' : ''} onClick={() => setId(s.id)} data-alt={s.id}>
            <b>{SHORT[s.id]}</b><small>{PLAIN[s.id]}</small>
          </button>
        ))}
      </div>
      <div className="c2-body">
        <div className="gl-col">
          <h3 className="gain">You gain <small>{gains.length}</small></h3>
          <ul>{gains.map((r) => <Item key={r.m.key} r={r} kind="gain" />)}</ul>
        </div>
        <div className="gl-col">
          <h3 className="loss">You give up <small>{losses.length}</small></h3>
          <ul>{losses.map((r) => <Item key={r.m.key} r={r} kind="loss" />)}</ul>
          {!losses.length && <p className="muted">Nothing clearly worse than today.</p>}
        </div>
        <div className="gl-col side">
          <div className="overall-card">
            <h3>Overall, on the six priorities</h3>
            <p>{overlapShare([oa.lo, oa.hi], [ot.lo, ot.hi]) > 0.5 ? 'Too close to call with today' : oa.v > ot.v ? 'Ahead of today' : 'Behind today'}: <b>{r0(oa.v)}</b> vs <b>{r0(ot.v)}</b> out of 100.</p>
            <Ranges min={0} max={50} ticks={3} height={16} items={[{ label: 'Today', lo: ot.lo, hi: ot.hi, v: ot.v, color: '#9aa3ad' }, { label: 'This', lo: oa.lo, hi: oa.hi, v: oa.v, color: '#8ab4f8' }]} />
            {ties.length > 0 && <p className="tie-line">≈ <b>Too close to call</b> with {ties.map((t) => SHORT[t.id]).join(' and ')}: their likely ranges overlap by more than half.</p>}
          </div>
          <h3>No clear difference <small>{unclear.length}</small></h3>
          <p className="muted small">{unclear.map((r) => r.m.label).join(' · ')}</p>
          <h3>Not counted yet <small>{none.length}</small></h3>
          <p className="muted small">{none.map((r) => r.m.label).join(' · ')}{none.length ? ' (no price data), ' : ''}insurance loss history (not processed).</p>
          <div className="howto mini">
            <p><b>Reading the bars:</b> each bar is the span of likely values (we don’t know crop water use or rain exactly); the dot is our best estimate. A gain counts only when the two bars don’t overlap.</p>
            <p className="muted">{WEATHER_LABEL[weather]}. Supports, doesn’t replace, your adviser.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
