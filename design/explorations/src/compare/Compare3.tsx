// Option 3 — two rotations head to head; sliders say what matters; a tug-of-war per priority and one verdict.
import { useState } from 'react';
import { DEFAULT_W, PLAIN, PRIORITIES, SHORT, STRATS, overall, overlapShare, r0, verdict } from '../data';
import { AssumedNote, Ranges } from '../ui';
import { UNIT_METRICS, Weather, WEATHER_LABEL } from './common';

const W_LABEL = ['Ignore', 'A little', 'Some', 'A lot', 'Most'];
const CA = '#8ab4f8', CB = '#ffb86b';

function Picker({ value, onChange, other, color, side }: { value: string; onChange: (id: string) => void; other: string; color: string; side: string }) {
  return (
    <div className="h2h-pick" style={{ borderColor: color }}>
      <small style={{ color }}>{side}</small>
      <div className="pick-list">
        {STRATS.map((s) => (
          <button key={s.id} disabled={s.id === other} className={s.id === value ? 'on' : ''} style={s.id === value ? { background: color, color: '#0b1016' } : undefined} onClick={() => onChange(s.id)} data-pick={`${side}-${s.id}`}>
            {SHORT[s.id]}
          </button>
        ))}
      </div>
      <p className="muted small">{PLAIN[value]}</p>
    </div>
  );
}

export default function Compare3({ weather, initA, initB }: { weather: Weather; initA?: string; initB?: string }) {
  const [a, setA] = useState(initA ?? 'car0_rice_winterflood');
  const [b, setB] = useState(initB ?? 'car1_rice_wintercover');
  const [w, setW] = useState<Record<string, number>>(DEFAULT_W);
  const A = STRATS.find((s) => s.id === a)!, B = STRATS.find((s) => s.id === b)!;
  const oa = overall(A, w), ob = overall(B, w);
  const share = overlapShare([oa.lo, oa.hi], [ob.lo, ob.hi]);
  const tie = share > 0.5;
  const lead = oa.v >= ob.v ? A : B;
  const ov: [number, number] | null = Math.min(oa.hi, ob.hi) > Math.max(oa.lo, ob.lo) ? [Math.max(oa.lo, ob.lo), Math.min(oa.hi, ob.hi)] : null;
  const maxAxis = Math.max(50, Math.ceil(Math.max(oa.hi, ob.hi) / 10) * 10);
  const wsum = Object.values(w).reduce((x, y) => x + y, 0) || 1;

  return (
    <section className="panel glass wide c3">
      <header className="ph row">
        <div>
          <h1>Which of these two fits what matters to you?</h1>
          <p className="headline">
            {tie
              ? <>With your priorities, <b style={{ color: CA }}>{SHORT[a]}</b> and <b style={{ color: CB }}>{SHORT[b]}</b> are <b>too close to call</b>: their likely scores overlap by {Math.round(share * 100)}%.</>
              : <><b style={{ color: lead === A ? CA : CB }}>{SHORT[lead.id]}</b> comes out ahead with your priorities: {r0(Math.max(oa.v, ob.v))} vs {r0(Math.min(oa.v, ob.v))} out of 100, and the likely ranges {ov ? 'barely' : 'don’t'} overlap.</>}
          </p>
        </div>
        <AssumedNote />
      </header>
      <div className="c3-body">
        <aside className="c3-weights">
          <h3>What matters to you?</h3>
          <p className="muted small">Drag to change how much each priority counts. The verdict updates as you go.</p>
          {PRIORITIES.map((p) => (
            <label key={p.key} className="wrow">
              <span><b>{p.label}</b><small>{p.plain}</small></span>
              <input type="range" min={0} max={4} step={1} value={w[p.key] ?? 0} onChange={(e) => setW({ ...w, [p.key]: +e.target.value })} />
              <em>{W_LABEL[w[p.key] ?? 0]}</em>
            </label>
          ))}
          <button className="link" onClick={() => setW(DEFAULT_W)}>Reset to equal</button>
        </aside>
        <div className="c3-main">
          <div className="h2h-picks">
            <Picker value={a} onChange={setA} other={b} color={CA} side="A" />
            <span className="vs">vs</span>
            <Picker value={b} onChange={setB} other={a} color={CB} side="B" />
          </div>

          <div className={`verdict ${tie ? 'tie' : ''}`}>
            <div className="verdict-word">{tie ? '≈ Too close to call' : `${lead === A ? 'A' : 'B'} is ahead`}</div>
            <Ranges min={0} max={maxAxis} ticks={6} height={22} overlap={ov}
              items={[{ label: 'A', lo: oa.lo, hi: oa.hi, v: oa.v, color: CA }, { label: 'B', lo: ob.lo, hi: ob.hi, v: ob.v, color: CB }]} />
            <p className="muted small">Bars show the span of likely overall scores; dots are best estimates.{ov && ' The shaded part is where they overlap.'} If the overlap covers more than half of the shorter bar, we call it a tie rather than pretend to rank.</p>
          </div>

          <h3>Who wins each priority <small className="muted">longer bar = bigger difference × how much you care</small></h3>
          <div className="tug">
            <div className="tug-head"><span style={{ color: CA }}>◀ A better</span><span style={{ color: CB }}>B better ▶</span></div>
            {PRIORITIES.map((p) => {
              const na = A.scores[p.key], nb = B.scores[p.key];
              const d = (nb.v ?? 0) - (na.v ?? 0);
              const unclear = verdict(nb, na) === 'unclear';
              const len = Math.min(50, (Math.abs(d) * (w[p.key] ?? 0)) / wsum * 3);
              return (
                <div key={p.key} className={`tug-row ${(w[p.key] ?? 0) === 0 ? 'off' : ''}`}>
                  <span className="tug-l">{p.label}</span>
                  <div className="tug-track">
                    <i className="mid" />
                    {d !== 0 && <i className={`bar ${unclear ? 'unclear' : ''}`} style={{ [d > 0 ? 'left' : 'right']: '50%', width: `${len}%`, background: unclear ? undefined : d > 0 ? CB : CA }} />}
                  </div>
                  <span className="tug-r">{d === 0 ? 'Same' : unclear ? 'Can’t tell' : `${r0(na.v)} vs ${r0(nb.v)}`}</span>
                </div>
              );
            })}
          </div>

          <h3>In real units <small className="muted">{WEATHER_LABEL[weather]}</small></h3>
          <div className="units">
            {UNIT_METRICS.map((m) => {
              const na = m.get(A, weather), nb = m.get(B, weather);
              return (
                <div key={m.key} className="unit">
                  <small>{m.label}</small>
                  <span><b style={{ color: CA }}>{m.fmt(na.v!)}</b></span>
                  <span><b style={{ color: CB }}>{m.fmt(nb.v!)}</b></span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
