// "Gain / give up vs today": pick one alternative and see two plain lists in acre-feet and days.
// The full side-by-side table (ported from design/explorations Compare1) is one click away.
import { Fragment, useMemo, useState } from 'react';
import type { CoverClass, Location, RotationStrategy, ScoreKey, SourcedNumber } from '../../types';
import { CLASS_COLOR, mmToAfac } from '../../lib';
import Icon from '../Icons';
import { openetText } from '../ui/shared';

type Weather = 'typical' | '2022' | '2023';
const WEATHER: Record<Weather, string> = { typical: 'Typical year', '2022': 'Dry, like 2022', '2023': 'Wet, like 2023' };
type Verdict = 'better' | 'worse' | 'unclear' | 'same' | 'none';
interface N { v: number | null; lo: number | null; hi: number | null }
interface Metric { key: string; label: string; unit: 'af' | 'days' | 'score'; higherIsBetter: boolean; get: (s: RotationStrategy, w: Weather) => N; gain: string; loss: string }

const n = (x?: SourcedNumber | null): N => (!x || x.blocked || x.value == null ? { v: null, lo: null, hi: null } : { v: x.value, lo: x.low ?? x.value, hi: x.high ?? x.value });
const af = (x: N): N => ({ v: x.v == null ? null : mmToAfac(x.v), lo: x.lo == null ? null : mmToAfac(x.lo), hi: x.hi == null ? null : mmToAfac(x.hi) });
const rep = (s: RotationStrategy, w: Weather, k: 'irrigation_need_mm' | 'exposed_rain_days') => (w === 'typical' ? null : s.exposure.replay[w]?.[k]);

const UNIT: Metric[] = [
  { key: 'water', label: 'Irrigation water needed', unit: 'af', higherIsBetter: false, get: (s, w) => af(n(rep(s, w, 'irrigation_need_mm') ?? s.water.irrigation_need_mm)), gain: 'Needs less irrigation water', loss: 'Needs more irrigation water' },
  { key: 'bare', label: 'Days the field sits bare', unit: 'days', higherIsBetter: false, get: (s) => n(s.exposure.bare_days_per_year), gain: 'Field bare fewer days', loss: 'Field bare more days' },
  { key: 'rain', label: 'Heavy rain on bare soil', unit: 'days', higherIsBetter: false, get: (s, w) => n(rep(s, w, 'exposed_rain_days') ?? s.exposure.exposed_rain_days), gain: 'Less heavy rain on bare soil', loss: 'More heavy rain on bare soil' },
  { key: 'heat', label: 'Hot days on bare soil (95 °F or more)', unit: 'days', higherIsBetter: false, get: (s) => n(s.exposure.exposed_heat_days), gain: 'Fewer hot days on bare soil', loss: 'More hot days on bare soil' },
];
const PLAIN: [ScoreKey, string, string, string, boolean][] = [
  ['forage_value', 'Feed you can cut or graze', 'More feed to cut or graze', 'Less feed to cut or graze', true],
  ['n_fixation', 'Adds nitrogen (legumes)', 'Adds more nitrogen', 'Adds less nitrogen', true],
  ['erosion', 'Protects soil from washing away', 'Better soil protection', 'Less soil protection', true],
  ['organic_matter', 'Builds organic matter', 'Builds more organic matter', 'Builds less organic matter', true],
  ['market', 'Crops you can sell locally', 'Easier to sell', 'Harder to sell', true],
  ['pest_break', 'Breaks pest cycles', 'Breaks pest cycles better', 'Breaks pest cycles less', false],
  ['infiltration', 'Water soaks in', 'Water soaks in better', 'Water soaks in less', false],
  ['n_scavenging', 'Holds nitrogen over winter', 'Holds more nitrogen over winter', 'Holds less nitrogen over winter', false],
];
const SCORE: Metric[] = PLAIN.map(([k, label, gain, loss]) => ({ key: k, label, unit: 'score', higherIsBetter: true, get: (s) => n(s.scores[k]), gain, loss }));
const MAIN_SCORES = new Set(PLAIN.filter((x) => x[4]).map((x) => x[0] as string));

function verdict(a: N, b: N, hib: boolean): Verdict {
  if (a.v == null || b.v == null) return 'none';
  const [aLo, aHi, bLo, bHi] = [a.lo ?? a.v, a.hi ?? a.v, b.lo ?? b.v, b.hi ?? b.v];
  if (aLo === bLo && aHi === bHi && a.v === b.v) return 'same';
  if (aLo > bHi) return hib ? 'better' : 'worse';
  if (aHi < bLo) return hib ? 'worse' : 'better';
  if (aLo === aHi && bLo === bHi) return a.v > b.v === hib ? 'better' : 'worse';
  return 'unclear';
}
const r1 = (x: number) => (Math.abs(x) < 10 ? x.toFixed(1) : Math.round(x).toLocaleString());
const fmt = (m: Metric, x: N) => (x.v == null ? 'not scored yet' : m.unit === 'af' ? `${x.v.toFixed(1)} acre-ft/acre` : m.unit === 'days' ? `${r1(x.v)} days a year` : `${Math.round(x.v)} of 100`);
const rng = (m: Metric, x: N) => (x.v == null ? '' : x.lo != null && x.hi != null && Math.abs(x.hi - x.lo) > (m.unit === 'af' ? 0.05 : 0.5) ? `likely ${m.unit === 'af' ? x.lo.toFixed(1) : Math.round(x.lo)}–${m.unit === 'af' ? x.hi.toFixed(1) : Math.round(x.hi)}` : '');
function delta(m: Metric, a: number, b: number) {
  const d = Math.abs(a - b);
  if (m.unit === 'af') return `about ${d.toFixed(1)} acre-ft/acre ${a < b ? 'less' : 'more'} a year (${(d * 12).toFixed(0)} in)`;
  if (m.unit === 'days') return `about ${r1(d)} ${a < b ? 'fewer' : 'more'} days a year`;
  return `${Math.round(a)} vs ${Math.round(b)} on a 0–100 rule of thumb`;
}

function Bars({ m, a, b, kind }: { m: Metric; a: N; b: N; kind: 'gain' | 'loss' }) {
  const max = m.unit === 'score' ? 100 : Math.max(a.hi ?? 0, b.hi ?? 0) * 1.1 || 1;
  const x = (v: number) => `${(v / max) * 100}%`;
  const row = (lab: string, v: N, cls: string) => (
    <div className="rg-row"><span>{lab}</span>
      <div className="rg-track"><i className={`rg-bar ${cls}`} style={{ left: x(v.lo ?? v.v ?? 0), width: `max(4px, calc(${x(v.hi ?? v.v ?? 0)} - ${x(v.lo ?? v.v ?? 0)}))` }} /><em style={{ left: x(v.v ?? 0) }} /></div>
    </div>
  );
  return <div className="ranges">{row('Today', b, 'today')}{row('This', a, kind)}</div>;
}

export default function ComparePanel(p: { loc: Location; strategies: RotationStrategy[]; allocation: number; setAllocation: (v: number) => void; onBrief: (id: string) => void; onClose: () => void }) {
  const today = p.strategies.find((s) => s.is_baseline) ?? p.strategies[0];
  const alts = p.strategies.filter((s) => s.id !== today.id);
  // open on the alternative that saves the most water: the question a grower under a water limit asks first
  const [id, setId] = useState(() => [...alts].sort((a, b) => a.water.irrigation_need_mm.value - b.water.irrigation_need_mm.value)[0]?.id);
  const [weather, setWeather] = useState<Weather>('typical');
  const [table, setTable] = useState(false);
  const alt = alts.find((s) => s.id === id) ?? alts[0];
  const all = [...UNIT, ...SCORE];
  const rows = useMemo(() => all.map((m) => { const a = m.get(alt, weather), b = m.get(today, weather); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; }), [alt, today, weather]); // eslint-disable-line react-hooks/exhaustive-deps
  const gains = rows.filter((r) => r.v === 'better'), losses = rows.filter((r) => r.v === 'worse');
  const unclear = rows.filter((r) => r.v === 'unclear' || r.v === 'same'), none = rows.filter((r) => r.v === 'none');
  const lead = (r: (typeof rows)[number] | undefined, k: 'gain' | 'loss') => (r ? `${r.m[k].toLowerCase()}, ${delta(r.m, r.a.v!, r.b.v!)}` : 'nothing clear');
  const water = (s: RotationStrategy) => af(n(rep(s, weather, 'irrigation_need_mm') ?? s.water.irrigation_need_mm));
  const fits = (s: RotationStrategy) => { const w = water(s); return (w.hi ?? 0) <= p.allocation ? 'Fits your limit' : (w.lo ?? 0) > p.allocation ? 'Over your limit' : 'May go over your limit'; };

  return (
    <section className="sheet compare2" data-testid="compare">
      <header className="sheet-head">
        <div>
          <h2>If you switched, what would you gain and what would you give up?</h2>
          <p className="sheet-lede"><b>{alt.short_name}</b> against what you do now ({today.short_name.toLowerCase()}): you’d gain <b className="good">{lead(gains[0], 'gain')}</b>. You’d give up <b className="bad">{lead(losses[0], 'loss')}</b>.</p>
        </div>
        <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>
      </header>
      <div className="c2-bar">
        <div className="c2-tabs">
          {alts.map((s) => (
            <button key={s.id} className={s.id === alt.id ? 'on' : ''} onClick={() => { setId(s.id); setTable(false); }} data-alt={s.id}>
              <b>{s.short_name}</b>
              <span className="month-strip">{s.month_cover.split('').map((c, m) => <i key={m} title={s.calendar_months[m]} style={{ background: CLASS_COLOR[c as CoverClass] }} />)}</span>
              <small>{(water(s).v ?? 0).toFixed(1)} acre-ft/acre · {fits(s).toLowerCase()}</small>
            </button>
          ))}
          <button className={`see-all ${table ? 'on' : ''}`} onClick={() => setTable(!table)} data-testid="see-all"><b>{table ? 'Back to gain / give up' : 'See all side by side'}</b><small>Every rotation, every factor</small></button>
        </div>
        <div className="c2-ctl">
          <label>Your water limit <b>{p.allocation.toFixed(1)} acre-ft/acre</b>
            <input type="range" min={0.5} max={6} step={0.1} value={p.allocation} onChange={(e) => p.setAllocation(+e.target.value)} data-testid="alloc" /></label>
          <div className="seg small">{(Object.keys(WEATHER) as Weather[]).map((w) => <button key={w} className={weather === w ? 'on' : ''} onClick={() => setWeather(w)} data-testid={`replay-${w}`}>{WEATHER[w]}</button>)}</div>
        </div>
      </div>

      {!table ? (
        <div className="c2-body">
          <div className="gl-col">
            <h3 className="gain">You gain</h3>
            <ul>{gains.map((r) => <li key={r.m.key} className="gl-item"><div className="gl-head"><b>{r.m.gain}</b><span>{delta(r.m, r.a.v!, r.b.v!)}</span></div><Bars m={r.m} a={r.a} b={r.b} kind="gain" /></li>)}</ul>
            {!gains.length && <p className="muted">Nothing clearly better than today.</p>}
          </div>
          <div className="gl-col">
            <h3 className="loss">You give up</h3>
            <ul>{losses.map((r) => <li key={r.m.key} className="gl-item"><div className="gl-head"><b>{r.m.loss}</b><span>{delta(r.m, r.a.v!, r.b.v!)}</span></div><Bars m={r.m} a={r.a} b={r.b} kind="loss" /></li>)}</ul>
            {!losses.length && <p className="muted">Nothing clearly worse than today.</p>}
          </div>
          <aside className="gl-col side">
            <h3>Water against your limit</h3>
            <p><b>{fits(alt)}</b>: needs {water(alt).v?.toFixed(1)} acre-ft/acre ({rng(UNIT[0], water(alt))}) ({WEATHER[weather].toLowerCase()}); today needs {water(today).v?.toFixed(1)}.</p>
            <p className="how">{openetText(p.strategies)} Only today’s rotation can be checked; the others use the same method.</p>
            <h3>No clear difference</h3>
            <p className="how">{unclear.map((r, i) => (i ? r.m.label.toLowerCase() : r.m.label)).join(', ') || 'None'}. The likely ranges overlap, so the inputs aren’t precise enough to say which is better.</p>
            <h3>Not counted yet</h3>
            <p className="how">{[...none.map((r) => r.m.label), 'Dollars per acre (no price data yet)', 'crop-insurance loss history'].map((x, i) => (i ? x.toLowerCase() : x)).join(', ')}.</p>
            <p className="how">Bars: the span of likely values; the tick is the best estimate. A gain counts only when the two spans don’t overlap.</p>
            <button className="btn primary wide" onClick={() => p.onBrief(alt.id)} data-testid="to-brief">Print this comparison for your adviser<Icon name="right" size={16} /></button>
          </aside>
        </div>
      ) : (
        <div className="c1-body">
          <table className="tt">
            <thead><tr><th /><th className="today">What you do now<small>{today.short_name}</small></th>{alts.map((s) => <th key={s.id}>Alternative<small>{s.short_name}</small></th>)}</tr></thead>
            <tbody>
              <tr className="grp"><td colSpan={alts.length + 2}>Water, days and weather · {WEATHER[weather].toLowerCase()}</td></tr>
              {[...UNIT, ...SCORE].map((m, i) => {
                const b = m.get(today, weather);
                return (
                  <Fragment key={m.key}>
                    {i === UNIT.length && <tr className="grp"><td colSpan={alts.length + 2}>Soil, feed and market · rules of thumb, 0 to 100, higher is better</td></tr>}
                    <tr className={m.unit === 'score' && !MAIN_SCORES.has(m.key) ? 'extra' : ''}>
                      <th>{m.label}</th>
                      <td className="today">{fmt(m, b)} <small>{rng(m, b)}</small></td>
                      {alts.map((s) => { const a = m.get(s, weather), v = verdict(a, b, m.higherIsBetter); return <td key={s.id}><span className={`vchip v-${v}`}>{v === 'better' ? 'Better' : v === 'worse' ? 'Worse' : v === 'none' ? 'Not scored' : 'Can’t tell'}</span> {fmt(m, a)} <small>{rng(m, a)}</small></td>; })}
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <footer className="sheet-foot">Better / worse = the whole likely range is above or below today’s. Rules of thumb from the rotation model, weather 2015–2025. Supports, doesn’t replace, your adviser.</footer>
    </section>
  );
}

/** Plain gain / give-up lines for the printable brief (typical year). */
export function tradeoffs(today: RotationStrategy, alt: RotationStrategy) {
  const rows = [...UNIT, ...SCORE].map((m) => { const a = m.get(alt, 'typical'), b = m.get(today, 'typical'); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; });
  const line = (r: (typeof rows)[number], k: 'gain' | 'loss') => (r.m.unit === 'score' ? `${r.m[k]} (rule of thumb).` : `${r.m[k]}: ${delta(r.m, r.a.v!, r.b.v!)}.`);
  return {
    gains: rows.filter((r) => r.v === 'better').map((r) => line(r, 'gain')),
    losses: rows.filter((r) => r.v === 'worse').map((r) => line(r, 'loss')),
    unclear: rows.filter((r) => r.v === 'unclear' || r.v === 'same').map((r) => r.m.label.toLowerCase()),
  };
}
