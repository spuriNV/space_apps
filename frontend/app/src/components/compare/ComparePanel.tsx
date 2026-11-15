// "Gain / give up vs today": pick one alternative and see two plain lists in acre-feet and days.
// The full side-by-side table (ported from design/explorations Compare1) is one click away.
import { useEffect, useMemo, useState } from 'react';
import type { Calendar, Location, RotationStrategy, ScoreKey, SourcedNumber } from '../../types';
import { scoreStrategies, type Scenario } from '../../api';
import { observedBare } from '../../bare';
import { useDetail } from '../ui/Detail';
import { mmToAfac } from '../../lib';
import Icon from '../Icons';
import { isBC } from '../ui/shared';
import { DockBottom } from '../ui/Dock';
import { SimRun } from './SimRun';
import type { SimMode } from '../ui/FieldTimeline';
import { HOT_F, hotBareDays, type Daily } from '../../season';

/** Hot days on bare soil per rotation: NOAA station highs >= 104 °F in the months the rotation leaves the field bare or thin. */
/** Per-field context: hot days on bare soil (NOAA stations) and bare days (satellite-seen for today, model for the others). */
export function fieldCtx(strategies: RotationStrategy[], daily: Daily | null, cal: Calendar | null): Ctx {
  const heat: Record<string, N> = {}, bare: Record<string, N> = {};
  if (daily) for (const s of strategies) { const h = hotBareDays(daily, s.month_cover); if (h) heat[s.id] = { v: h.value, lo: h.value, hi: h.value }; }
  const ob = observedBare(cal), today = strategies.find((s) => s.is_baseline);
  if (ob && today) bare[today.id] = { v: ob.value, lo: ob.value, hi: ob.value };
  return { heat, bare, bareYears: ob?.years ?? [] };
}
export const HEAT_NOTE = `Hot days = NOAA weather-station highs of ${HOT_F} °F or more, in months the rotation leaves the field bare.`;

type Weather = 'typical' | '2022' | '2023';
const weatherLabels = (bc: boolean): Record<Weather, string> => bc
  ? { typical: 'Typical year', '2022': 'Drier year', '2023': 'Restricted water, like 2023' }
  : { typical: 'Typical year', '2022': 'Dry, like 2022', '2023': 'Wet, like 2023' };
type Verdict = 'better' | 'worse' | 'unclear' | 'same' | 'none';
interface N { v: number | null; lo: number | null; hi: number | null }
/** Per-field context the metrics need: hot days on bare soil per rotation, from NOAA station highs. */
interface Ctx { heat: Record<string, N>; bare: Record<string, N>; bareYears: number[] }
interface Metric { key: string; label: string; unit: 'af' | 'days' | 'score'; higherIsBetter: boolean; get: (s: RotationStrategy, w: Weather, c: Ctx) => N; gain: string; loss: string }

const n = (x?: SourcedNumber | null): N => (!x || x.blocked || x.value == null ? { v: null, lo: null, hi: null } : { v: x.value, lo: x.low ?? x.value, hi: x.high ?? x.value });
const af = (x: N): N => ({ v: x.v == null ? null : mmToAfac(x.v), lo: x.lo == null ? null : mmToAfac(x.lo), hi: x.hi == null ? null : mmToAfac(x.hi) });
const rep = (s: RotationStrategy, w: Weather, k: 'irrigation_need_mm' | 'exposed_rain_days') => (w === 'typical' ? null : s.exposure.replay[w]?.[k]);

const UNIT: Metric[] = [
  { key: 'water', label: 'Irrigation water needed', unit: 'af', higherIsBetter: false, get: (s, w) => af(n(rep(s, w, 'irrigation_need_mm') ?? s.water.irrigation_need_mm)), gain: 'Needs less irrigation water', loss: 'Needs more irrigation water' },
  { key: 'bare', label: 'Days the field sits bare', unit: 'days', higherIsBetter: false, get: (s, _w, c) => c.bare[s.id] ?? n(s.exposure.bare_days_per_year), gain: 'Field bare fewer days', loss: 'Field bare more days' },
  { key: 'rain', label: 'Heavy rain on bare soil', unit: 'days', higherIsBetter: false, get: (s, w) => n(rep(s, w, 'exposed_rain_days') ?? s.exposure.exposed_rain_days), gain: 'Less heavy rain on bare soil', loss: 'More heavy rain on bare soil' },
  { key: 'heat', label: 'Hot days on bare soil (104 °F or more)', unit: 'days', higherIsBetter: false, get: (s, _w, c) => c.heat[s.id] ?? { v: null, lo: null, hi: null }, gain: 'Fewer hot days on bare soil', loss: 'More hot days on bare soil' },
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
function delta(m: Metric, a: number, b: number) {
  const d = Math.abs(a - b);
  if (m.unit === 'af') return `about ${d.toFixed(1)} acre-ft/acre ${a < b ? 'less' : 'more'} a year (${(d * 12).toFixed(0)} in)`;
  if (m.unit === 'days') return `about ${r1(d)} ${a < b ? 'fewer' : 'more'} days a year`;
  return `${Math.round(a)} vs ${Math.round(b)} on a 0–100 rule of thumb`;
}

const PRIORITIES: [ScoreKey, string][] = [['water_use', 'Saving water'], ['forage_value', 'Feed to cut or graze'], ['n_fixation', 'Adding nitrogen'], ['erosion', 'Keeping soil in place'], ['organic_matter', 'Building organic matter'], ['pest_break', 'Breaking pest cycles']];
const RAIN: [number, string][] = [[-20, '20% less rain'], [0, 'Normal rain'], [20, '20% more rain']];
const HEAT: [number, string][] = [[0, 'Normal heat'], [2, '4 °F warmer'], [4, '7 °F warmer']];
/** Scores that are the same for every rotation on this field carry no information: list them as "not scored yet". */
const constantScores = (ss: RotationStrategy[]) => new Set(SCORE.filter((m) => { const v = ss.map((s) => s.scores[m.key as ScoreKey]?.value); return v.every((x) => x == null || x === v[0]); }).map((m) => m.key));

export default function ComparePanel(p: {
  loc: Location; strategies: RotationStrategy[]; daily: Daily | null; cal: Calendar | null; live: boolean;
  allocation: number; exampleLimit: boolean; setAllocation: (v: number) => void; onBrief: (id: string) => void; onClose: () => void;
  sim: SimMode; simRunning: boolean; onRunSim: (sim: NonNullable<SimMode>, startT: number) => void; onStopSim: () => void;
}) {
  // farmer priorities (0-4) and a rain / temperature what-if, re-scored by the rotation model (POST /score)
  const [weights, setWeights] = useState<Partial<Record<ScoreKey, number>>>({});
  const [scen, setScen] = useState<Scenario>({ dT_c: 0, dP_pct: 0 });
  const [rescored, setRescored] = useState<{ key: string; items: RotationStrategy[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const custom = Object.keys(weights).length > 0 || scen.dT_c !== 0 || scen.dP_pct !== 0;
  const key = JSON.stringify([weights, scen, p.allocation, p.loc.id]);
  useEffect(() => {
    if (!custom || !p.live) return;
    setBusy(true);
    const h = setTimeout(() => scoreStrategies(p.loc.id, p.allocation, { ...Object.fromEntries(PRIORITIES.map(([k]) => [k, k === 'pest_break' ? 0 : 1])), market: 0, ...weights }, scen)
      .then((st) => { if (st) setRescored({ key, items: st }); }).finally(() => setBusy(false)), 400);
    return () => clearTimeout(h);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const strategies = custom && rescored?.key === key ? rescored.items.map((s) => ({ ...s, water: { ...s.water, etc_vs_openet_pct: p.strategies.find((x) => x.id === s.id)?.water.etc_vs_openet_pct ?? null } })) : p.strategies;
  const ctx = useMemo(() => fieldCtx(strategies, p.daily, p.cal), [strategies, p.daily, p.cal]);
  const flat = useMemo(() => constantScores(strategies), [strategies]);
  const today = strategies.find((s) => s.is_baseline) ?? strategies[0];
  const detail = useDetail().on;
  const allAlts = strategies.filter((s) => s.id !== today.id);
  const alts = detail ? allAlts : [...allAlts].sort((a, b) => b.composite.value - a.composite.value).slice(0, 2);
  const [id, setId] = useState(() => [...alts].sort((a, b) => a.water.irrigation_need_mm.value - b.water.irrigation_need_mm.value)[0]?.id);
  const [weather, setWeather] = useState<Weather>('typical');
  const [focus, setFocus] = useState<ScoreKey | null>(null);
  const alt = alts.find((s) => s.id === id) ?? alts[0];
  const heavy = p.loc.soil.hydrologic_group === 'D';
  const label = (m: Metric) => (m.key === 'infiltration' && heavy ? { ...m, gain: `${m.gain} (small effect on this heavy, slow-draining soil)`, loss: `${m.loss} (small effect on this heavy soil)` } : m);
  const all = detail ? [...UNIT, ...SCORE.filter((m) => !flat.has(m.key)).map(label)] : UNIT;
  const rows = useMemo(() => all.map((m) => { const a = m.get(alt, weather, ctx), b = m.get(today, weather, ctx); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; }), [alt, today, weather, ctx, flat, detail]); // eslint-disable-line react-hooks/exhaustive-deps
  const gains = rows.filter((r) => r.v === 'better'), losses = rows.filter((r) => r.v === 'worse');
  const lead = (r: (typeof rows)[number] | undefined, k: 'gain' | 'loss') => (r ? `${r.m[k].toLowerCase()}, ${delta(r.m, r.a.v!, r.b.v!)}` : 'nothing clear');
  const water = (s: RotationStrategy) => af(n(rep(s, weather, 'irrigation_need_mm') ?? s.water.irrigation_need_mm));
  const fits = (s: RotationStrategy) => { const w = water(s); return (w.hi ?? 0) <= p.allocation ? 'Fits your limit' : (w.lo ?? 0) > p.allocation ? 'Over your limit' : 'May go over your limit'; };
  const ranked = [...strategies].sort((a, b) => b.composite.value - a.composite.value);
  const tie = ranked.length > 1 && (ranked[0].composite.low ?? 0) <= (ranked[1].composite.high ?? 0);
  const WEATHER = weatherLabels(isBC(p.loc));

  const setPrimary = (k: ScoreKey) => {
    setFocus(k);
    const next: Partial<Record<ScoreKey, number>> = {};
    for (const [id] of PRIORITIES) next[id] = id === k ? 4 : id === 'pest_break' ? 0 : 1;
    setWeights(next);
  };

  return (
    <section className="sheet compare2 talk" data-testid="compare">
      <header className="sheet-head">
        <div>
          <h2>Your call</h2>
          <p className="sheet-lede">Set knobs. Results under the map.</p>
        </div>
      </header>

      <div className="c2-inputs" data-testid="farmer-inputs">
        <div className="c2-in-block">
          <h3>Water limit <b className="c2-inline">{p.allocation.toFixed(1)} acre-ft/acre</b></h3>
          {p.exampleLimit && <p className="how"><em className="ex-limit">example — drag to yours</em></p>}
          <label className="c2-alloc">
            <input type="range" min={0.5} max={6} step={0.1} value={p.allocation} onChange={(e) => p.setAllocation(+e.target.value)} data-testid="alloc" aria-label="Water limit in acre-feet per acre" />
          </label>
        </div>
        <div className="c2-in-block">
          <h3>What matters most</h3>
          <div className="c2-focus" role="group" aria-label="What matters most">
            {PRIORITIES.map(([k, lab]) => (
              <button key={k} type="button" className={focus === k ? 'on' : ''} onClick={() => setPrimary(k)} disabled={!p.live} data-testid={`focus-${k}`}>{lab}</button>
            ))}
          </div>
        </div>
        <div className="c2-in-block">
          <h3>What if</h3>
          <div className="seg small wrap">{RAIN.map(([v, l]) => <button key={v} className={scen.dP_pct === v ? 'on' : ''} onClick={() => setScen({ ...scen, dP_pct: v })} disabled={!p.live} data-testid={`rain-${v}`}>{l}</button>)}</div>
          <div className="seg small wrap">{HEAT.map(([v, l]) => <button key={v} className={scen.dT_c === v ? 'on' : ''} onClick={() => setScen({ ...scen, dT_c: v })} disabled={!p.live}>{l}</button>)}</div>
          <p className="how">{busy ? 'Updating…' : !p.live ? 'Server offline — saved scores only.' : custom ? 'Using your settings.' : 'Even weights, normal weather.'}</p>
        </div>
        <SimRun
          loc={p.loc}
          strategies={strategies}
          allocation={p.allocation}
          pickId={alt?.id ?? id ?? null}
          weather={weather}
          setWeather={setWeather}
          onRun={p.onRunSim}
          running={p.simRunning}
          onStop={p.onStopSim}
        />
      </div>

      <DockBottom>
        <div className="bottom-inner c2-bottom" data-testid="compare-bottom">
          <div className="c2-rank-block">
            <p className="bottom-label">Best fit {busy ? '· updating…' : ''}</p>
            <ol className="rank" data-testid="farmer-rank">
              {ranked.map((s, i) => (
                <li key={s.id} className={`${s.is_baseline ? 'base' : ''} ${s.id === alt?.id ? 'pick' : ''}`}>
                  <button type="button" onClick={() => setId(s.id)}>
                    <b>{i + 1}. {s.short_name}</b>{s.is_baseline ? <em>today</em> : null}
                    <small>{(water(s).v ?? 0).toFixed(1)} af/ac · {fits(s).toLowerCase()}</small>
                  </button>
                </li>
              ))}
            </ol>
            {tie && <p className="how">Top two are too close to call.</p>}
          </div>
          <div className="c2-trade">
            <p className="c2-bar-lede">{alt ? <><b>{alt.short_name}</b> vs today: gain <b className="good">{lead(gains[0], 'gain')}</b>; give up <b className="bad">{lead(losses[0], 'loss')}</b>.</> : 'Pick a rotation.'}</p>
            <div className="c2-mini">
              <div>
                <h3 className="gain">You gain</h3>
                <ul>{gains.slice(0, 2).map((r) => <li key={r.m.key}><b>{r.m.gain}</b> — {delta(r.m, r.a.v!, r.b.v!)}</li>)}</ul>
                {!gains.length && <p className="muted">Nothing clear.</p>}
              </div>
              <div>
                <h3 className="loss">You give up</h3>
                <ul>{losses.slice(0, 2).map((r) => <li key={r.m.key}><b>{r.m.loss}</b> — {delta(r.m, r.a.v!, r.b.v!)}</li>)}</ul>
                {!losses.length && <p className="muted">Nothing clear.</p>}
              </div>
            </div>
            <p className="how"><b>{fits(alt)}</b> · needs {water(alt).v?.toFixed(1)} acre-ft/acre ({WEATHER[weather].toLowerCase()}).</p>
            <button className="btn primary" onClick={() => p.onBrief(alt.id)} data-testid="to-brief">Print this for your adviser<Icon name="right" size={16} /></button>
          </div>
        </div>
      </DockBottom>
    </section>
  );
}

/** Plain gain / give-up lines for the printable brief (typical year). */
export function tradeoffs(today: RotationStrategy, alt: RotationStrategy, ctx: Ctx, all: RotationStrategy[], heavySoil = false) {
  const flat = constantScores(all);
  const rows = [...UNIT, ...SCORE.filter((m) => !flat.has(m.key))].map((m) => { const a = m.get(alt, 'typical', ctx), b = m.get(today, 'typical', ctx); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; });
  const line = (r: (typeof rows)[number], k: 'gain' | 'loss') => (r.m.unit === 'score' ? `${r.m[k]} (rule of thumb${r.m.key === 'infiltration' && heavySoil ? '; small effect on this heavy soil' : ''}).` : `${r.m[k]}: ${delta(r.m, r.a.v!, r.b.v!)}.`);
  return {
    gains: rows.filter((r) => r.v === 'better').map((r) => line(r, 'gain')),
    losses: rows.filter((r) => r.v === 'worse').map((r) => line(r, 'loss')),
    unclear: rows.filter((r) => r.v === 'unclear' || r.v === 'same').map((r) => r.m.label.toLowerCase()),
  };
}
