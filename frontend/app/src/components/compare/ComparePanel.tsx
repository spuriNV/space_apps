// "Gain / give up vs today": pick one alternative and see two plain lists in acre-feet and days.
// The full side-by-side table (ported from design/explorations Compare1) is one click away.
import { Seg } from '../ui/Seg';
import { Fragment, useEffect, useMemo, useState } from 'react';
import type { Calendar, CoverClass, Location, RotationStrategy, ScoreKey, SourcedNumber } from '../../types';
import { scoreStrategies, type Scenario } from '../../api';
import { BARE_DEF, observedBare } from '../../bare';
import { What } from '../ui/What';
import { MoreDetail, useDetail } from '../ui/Detail';
import { CLASS_COLOR, RAIN_FED, isRainFed, mmToAfac, needText } from '../../lib';
import Icon from '../Icons';
import { openetText } from '../ui/shared';
import { HOT_F, hotBareDays, type Daily } from '../../season';
import { SimRun } from './SimRun';
import type { SimMode } from '../ui/FieldTimeline';

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
const WEATHER: Record<Weather, string> = { typical: 'Typical year', '2022': 'Dry, like 2022', '2023': 'Wet, like 2023' };
type Verdict = 'better' | 'worse' | 'unclear' | 'same' | 'none';
interface N { v: number | null; lo: number | null; hi: number | null; rf?: boolean }
/** Per-field context the metrics need: hot days on bare soil per rotation, from NOAA station highs. */
interface Ctx { heat: Record<string, N>; bare: Record<string, N>; bareYears: number[] }
interface Metric { key: string; label: string; unit: 'af' | 'days' | 'score'; higherIsBetter: boolean; get: (s: RotationStrategy, w: Weather, c: Ctx) => N; gain: string; loss: string }

const n = (x?: SourcedNumber | null): N => (!x || x.blocked || x.value == null ? { v: null, lo: null, hi: null } : { v: x.value, lo: x.low ?? x.value, hi: x.high ?? x.value });
const af = (x: N): N => ({ v: x.v == null ? null : mmToAfac(x.v), lo: x.lo == null ? null : mmToAfac(x.lo), hi: x.hi == null ? null : mmToAfac(x.hi) });
const rep = (s: RotationStrategy, w: Weather, k: 'irrigation_need_mm' | 'exposed_rain_days') => (w === 'typical' ? null : s.exposure.replay[w]?.[k]);

/** Irrigation need in acre-ft/acre; `rf` marks a rain-fed rotation, which reads as a label, not 0.0. */
const waterOf = (s: RotationStrategy, w: Weather): N => ({ ...af(n(rep(s, w, 'irrigation_need_mm') ?? s.water.irrigation_need_mm)), rf: isRainFed(s) });

const UNIT: Metric[] = [
  { key: 'water', label: 'Irrigation water needed', unit: 'af', higherIsBetter: false, get: (s, w) => waterOf(s, w), gain: 'Needs less irrigation water', loss: 'Needs more irrigation water' },
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
const fmt = (m: Metric, x: N) => (x.v == null ? 'not scored yet' : m.unit === 'af' && x.rf ? RAIN_FED : m.unit === 'af' ? `${x.v.toFixed(1)} acre-ft/acre` : m.unit === 'days' ? `${r1(x.v)} days a year` : `${Math.round(x.v)} of 100`);
const rng = (m: Metric, x: N) => (x.v == null ? '' : x.lo != null && x.hi != null && Math.abs(x.hi - x.lo) > (m.unit === 'af' ? 0.05 : 0.5) ? `likely ${m.unit === 'af' ? x.lo.toFixed(1) : Math.round(x.lo)}–${m.unit === 'af' ? x.hi.toFixed(1) : Math.round(x.hi)}` : '');
function delta(m: Metric, an: N, bn: N) {
  const a = an.v!, b = bn.v!, d = Math.abs(a - b);
  if (m.unit === 'af' && an.rf) return 'No irrigation needed (rain-fed)';
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

const PRIORITIES: [ScoreKey, string][] = [['water_use', 'Saving water'], ['forage_value', 'Feed to cut or graze'], ['n_fixation', 'Adding nitrogen'], ['erosion', 'Keeping soil in place'], ['organic_matter', 'Building organic matter'], ['pest_break', 'Breaking pest cycles']];
const LEVEL = ['Not at all', 'Normal', 'More', 'Much more', 'Top priority'];
const RAIN: [number, string][] = [[-20, '20% less rain'], [0, 'Normal rain'], [20, '20% more rain']];
const HEAT: [number, string][] = [[0, 'Normal heat'], [2, '4 °F warmer'], [4, '7 °F warmer']];
/** Scores that are the same for every rotation on this field carry no information: list them as "not scored yet". */
const constantScores = (ss: RotationStrategy[]) => new Set(SCORE.filter((m) => { const v = ss.map((s) => s.scores[m.key as ScoreKey]?.value); return v.every((x) => x == null || x === v[0]); }).map((m) => m.key));

export default function ComparePanel(p: { loc: Location; strategies: RotationStrategy[]; daily: Daily | null; cal: Calendar | null; live: boolean; allocation: number; exampleLimit: boolean; setAllocation: (v: number) => void; onBrief: (id: string) => void; sim: SimMode; simRunning: boolean; onRunSim: (sim: NonNullable<SimMode>, startT: number) => void; onStopSim: () => void; onClose: () => void }) {
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
  // farmer default: the two best-scoring alternatives; every option behind "See all options" or More detail
  const alts = detail ? allAlts : [...allAlts].sort((a, b) => b.composite.value - a.composite.value).slice(0, 2);
  // open on the alternative that saves the most water: the question a grower under a water limit asks first
  const [id, setId] = useState(() => [...alts].sort((a, b) => a.water.irrigation_need_mm.value - b.water.irrigation_need_mm.value)[0]?.id);
  const [weather, setWeather] = useState<Weather>('typical');
  const [table, setTable] = useState(false);
  const [tune, setTune] = useState(false);
  const alt = alts.find((s) => s.id === id) ?? alts[0];
  const heavy = p.loc.soil.hydrologic_group === 'D';
  const label = (m: Metric) => (m.key === 'infiltration' && heavy ? { ...m, gain: `${m.gain} (small effect on this heavy, slow-draining soil)`, loss: `${m.loss} (small effect on this heavy soil)` } : m);
  const all = detail ? [...UNIT, ...SCORE.filter((m) => !flat.has(m.key)).map(label)] : UNIT;
  const rows = useMemo(() => all.map((m) => { const a = m.get(alt, weather, ctx), b = m.get(today, weather, ctx); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; }), [alt, today, weather, ctx, flat, detail]); // eslint-disable-line react-hooks/exhaustive-deps
  const gains = rows.filter((r) => r.v === 'better'), losses = rows.filter((r) => r.v === 'worse');
  const unclear = rows.filter((r) => r.v === 'unclear' || r.v === 'same'), none = rows.filter((r) => r.v === 'none');
  const water = (s: RotationStrategy) => waterOf(s, weather);
  const fits = (s: RotationStrategy) => { const w = water(s); if (w.rf) return 'Fits your limit'; return (w.hi ?? 0) <= p.allocation ? 'Fits your limit' : (w.lo ?? 0) > p.allocation ? 'Over your limit' : 'May go over your limit'; };
  const ranked = [...strategies].sort((a, b) => b.composite.value - a.composite.value);
  const tie = ranked.length > 1 && (ranked[0].composite.low ?? 0) <= (ranked[1].composite.high ?? 0);

  return (
    <section className="sheet compare2" data-testid="compare">
      <header className="sheet-head">
        <div>
          <h2>{alt.short_name} vs {today.short_name.split(' +')[0].replace(/\s*\(current\)$/i, '').toLowerCase()} today</h2>
        </div>
        <button className="icon-btn" onClick={p.onClose} title="Close" aria-label="Close"><Icon name="close" size={16} /></button>
      </header>
      <div className="c2-bar">
        <div className="c2-tabs">
          {alts.map((s) => (
            <button key={s.id} className={s.id === alt.id ? 'on' : ''} onClick={() => { setId(s.id); setTable(false); }} data-alt={s.id}>
              <b>{s.short_name}</b>
              <span className="month-strip">{s.month_cover.split('').map((c, m) => <i key={m} title={s.calendar_months[m]} style={{ background: CLASS_COLOR[c as CoverClass] }} />)}</span>
              <small>{needText(s, water(s).v ?? 0)} · {fits(s).toLowerCase()}</small>
            </button>
          ))}
          <button className={`see-all ${table ? 'on' : ''}`} onClick={() => setTable(!table)} data-testid="see-all"><b>{table ? 'Back to gain / give up' : 'See all options'}</b><small>Every rotation, every factor</small></button>
        </div>
        <div className="c2-ctl">
          <label>Your water limit <b>{p.allocation.toFixed(1)} acre-ft/acre</b>{p.exampleLimit && <em className="status example ex-limit">example, change to yours</em>}
            <input type="range" min={0.5} max={6} step={0.1} value={p.allocation} onChange={(e) => p.setAllocation(+e.target.value)} data-testid="alloc" /></label>
          <Seg className="small" label="Weather" value={weather} onChange={setWeather} options={(Object.keys(WEATHER) as Weather[]).map((w) => ({ v: w, label: WEATHER[w], testid: `replay-${w}` }))} />
          <button className={`link tune-btn d-only ${tune ? 'on' : ''}`} onClick={() => setTune(!tune)} data-testid="tune">{tune ? 'Hide priorities and what-ifs' : 'Your priorities, and what if it’s drier or hotter'}</button>
        </div>
      </div>
      {tune && detail && (
        <div className="c2-tune" data-testid="tune-panel">
          <div className="tune-pri">
            <h4>What matters to you</h4>
            {PRIORITIES.map(([k, lab]) => {
              const v = weights[k] ?? (k === 'pest_break' ? 0 : 1);
              return (
                <div key={k} className="pri-row"><span>{lab}</span>
                  <Seg className="small" label={lab} value={v} onChange={(i) => setWeights({ ...weights, [k]: i })} options={LEVEL.map((l, i) => ({ v: i, label: l, disabled: !p.live }))} />
                </div>
              );
            })}
          </div>
          <div className="tune-what">
            <h4>What if the year is</h4>
            <Seg className="small" label="Rain" value={scen.dP_pct} onChange={(v) => setScen({ ...scen, dP_pct: v })} options={RAIN.map(([v, l]) => ({ v, label: l, disabled: !p.live, testid: `rain-${v}` }))} />
            <Seg className="small" label="Heat" value={scen.dT_c} onChange={(v) => setScen({ ...scen, dT_c: v })} options={HEAT.map(([v, l]) => ({ v, label: l, disabled: !p.live }))} />
            <p className="how">{!p.live ? 'Needs the CropLytics server; showing the saved scores.' : busy ? 'Re-scoring…' : custom ? 'Water need and ranking below use your settings.' : 'Default: every priority counts the same, normal weather.'}</p>
            <h4>Best fit for what matters to you</h4>
            <ol className="rank">{ranked.map((s, i) => <li key={s.id} className={s.is_baseline ? 'base' : ''}>{s.short_name}{s.is_baseline ? ' (today)' : ''}{i === 0 && tie ? <small> too close to call with the next one</small> : null}</li>)}</ol>
          </div>
        </div>
      )}

      {!table ? (
        <div className="c2-body">
          <div className="gl-col">
            <h3 className="gain">You gain</h3>
            <ul>{gains.map((r) => <li key={r.m.key} className="gl-item"><div className="gl-head"><b>{r.m.gain}</b><span>{delta(r.m, r.a, r.b)}</span></div><Bars m={r.m} a={r.a} b={r.b} kind="gain" /></li>)}</ul>
            {!gains.length && <p className="muted">Nothing clearly better than today.</p>}
          </div>
          <div className="gl-col">
            <h3 className="loss">You give up</h3>
            <ul>{losses.map((r) => <li key={r.m.key} className="gl-item"><div className="gl-head"><b>{r.m.loss}</b><span>{delta(r.m, r.a, r.b)}</span></div><Bars m={r.m} a={r.a} b={r.b} kind="loss" /></li>)}</ul>
            {!losses.length && <p className="muted">Nothing clearly worse than today.</p>}
          </div>
          <aside className="gl-col side">
            <h3>Water against your limit <What k="waterBalance" /></h3>
            <p><b>{fits(alt)}.</b> {isRainFed(alt) ? RAIN_FED : `Needs ${water(alt).v?.toFixed(1)} acre-ft/acre`}. Your limit: {p.allocation.toFixed(1)}.</p>
            <p className="how d-only">{rng(UNIT[0], water(alt)) ? `${rng(UNIT[0], water(alt)).replace(/^likely/, 'Likely')} acre-ft/acre, ` : ''}{WEATHER[weather].toLowerCase()}. {isRainFed(today) ? `Today is ${RAIN_FED.toLowerCase()}.` : `Today needs ${water(today).v?.toFixed(1)}.`}{/safflower|wheat/i.test(alt.name) ? ' An upper bound: soil water stored over winter is not counted.' : ''}</p>
            <p className="how d-only">{openetText(p.strategies)} That checks crop water use for today’s crop only; irrigation need and the other rotations use the same method, unchecked.</p>
            <div className="d-only">
            <h3>Bare days <What k="bare" /></h3>
            <p className="how">Today: {ctx.bare[today.id]?.v != null ? `${ctx.bare[today.id].v} days a year, seen by satellite ${ctx.bareYears[0]}–${ctx.bareYears[ctx.bareYears.length - 1]}` : `${Math.round(today.exposure.bare_days_per_year.value)} days a year (estimated)`}. Other rotations: estimated by the rotation model. {BARE_DEF}</p>
            <p className="how">Bars: the span of likely values; the tick is the best estimate. A gain counts only when the two spans don’t overlap.</p>
            </div>
            <SimRun loc={p.loc} strategies={p.strategies} allocation={p.allocation} pickId={alt.id} weather={weather} setWeather={setWeather} onRun={p.onRunSim} running={p.simRunning} onStop={p.onStopSim} />
            <MoreDetail what="All rotations and what-ifs" />
            <button className="btn btn-primary wide" onClick={() => p.onBrief(alt.id)} data-testid="to-brief">Print this comparison for your adviser<Icon name="right" size={16} /></button>
          </aside>
        </div>
      ) : (
        <div className="c1-body">
          <table className="tt">
            <thead><tr><th /><th className="today">What you do now<small>{today.short_name}</small></th>{allAlts.map((s) => <th key={s.id}>Alternative<small>{s.short_name}</small></th>)}</tr></thead>
            <tbody>
              <tr className="grp"><td colSpan={allAlts.length + 2}>Water, days and weather · {WEATHER[weather].toLowerCase()}</td></tr>
              {[...UNIT, ...SCORE.filter((m) => !flat.has(m.key)).map(label)].map((m, i) => {
                const b = m.get(today, weather, ctx);
                return (
                  <Fragment key={m.key}>
                    {i === UNIT.length && <tr className="grp"><td colSpan={allAlts.length + 2}>Soil, feed and pests · rules of thumb, 0 to 100, higher is better</td></tr>}
                    <tr className={m.unit === 'score' && !MAIN_SCORES.has(m.key) ? 'extra' : ''}>
                      <th>{m.label}</th>
                      <td className="today">{fmt(m, b)} <small>{rng(m, b)}</small></td>
                      {allAlts.map((s) => { const a = m.get(s, weather, ctx), v = verdict(a, b, m.higherIsBetter); return <td key={s.id}><span className={`vchip v-${v}`}>{v === 'better' ? 'Better' : v === 'worse' ? 'Worse' : v === 'none' ? 'Not scored' : 'Can’t tell'}</span> {fmt(m, a)} <small>{rng(m, a)}</small></td>; })}
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <footer className="sheet-foot">Better / worse = the whole likely range is above or below today’s. Water need: rotation model with NASA POWER weather, 2015–2025. {p.loc.region === 'bc' ? HEAT_NOTE.replace('NOAA', 'Environment Canada') : HEAT_NOTE} Supports, doesn’t replace, your adviser.</footer>
    </section>
  );
}

/** Plain gain / give-up lines for the printable brief (typical year). */
export function tradeoffs(today: RotationStrategy, alt: RotationStrategy, ctx: Ctx, all: RotationStrategy[], heavySoil = false) {
  const flat = constantScores(all);
  const rows = [...UNIT, ...SCORE.filter((m) => !flat.has(m.key))].map((m) => { const a = m.get(alt, 'typical', ctx), b = m.get(today, 'typical', ctx); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; });
  const line = (r: (typeof rows)[number], k: 'gain' | 'loss') => (r.m.unit === 'score' ? `${r.m[k]} (rule of thumb${r.m.key === 'infiltration' && heavySoil ? '; small effect on this heavy soil' : ''}).` : `${r.m[k]}: ${delta(r.m, r.a, r.b)}.`);
  return {
    gains: rows.filter((r) => r.v === 'better').map((r) => line(r, 'gain')),
    losses: rows.filter((r) => r.v === 'worse').map((r) => line(r, 'loss')),
    unclear: rows.filter((r) => r.v === 'unclear' || r.v === 'same').map((r) => r.m.label.toLowerCase()),
  };
}
