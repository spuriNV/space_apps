// "Gain / give up vs today": pick one alternative and see two plain lists in acre-feet and days.
// The full side-by-side table (ported from design/explorations Compare1) is one click away.
import { Seg } from '../ui/Seg';
import { Fragment, useEffect, useMemo, useState } from 'react';
import type { Calendar, CoverClass, Location, RotationStrategy, ScoreKey, SourcedNumber } from '../../types';
import { scoreStrategies, withToday, type Scenario } from '../../api';
import { BARE_DEF, observedBare } from '../../bare';
import { What } from '../ui/What';
import { useDetail } from '../ui/Detail';
import { Answer, Choice, StepShell } from '../ui/StepShell';
import { CLASS_COLOR, RAIN_FED, isRainFed, mmToAfac } from '../../lib';
import { fieldName, openetText, rotName } from '../ui/shared';
import { HOT_F, hotBareDays, type Daily } from '../../season';
import { SimRun } from './SimRun';
import { WaterBars } from './WaterBars';
import { acres as fieldAcres } from '../ui/shared';
import type { SimMode } from '../ui/FieldTimeline';
import { type Weather, WEATHER_LABEL, weatherLabels, waterOf as waterOfAf, scenarioBlurb, fitsLimit } from './weatherReplay';

/** Hot days on bare soil per rotation: NOAA station highs >= 104 °F in the months the rotation leaves the field bare or thin. */
/** Per-field context: hot days on bare soil (NOAA stations) and bare days (satellite-seen for today, model for the others). */
export function fieldCtx(strategies: RotationStrategy[], daily: Daily | null, cal: Calendar | null): Ctx {
  const heat: Record<string, N> = {}, bare: Record<string, N> = {};
  if (daily) for (const s of strategies) { const h = hotBareDays(daily, s.month_cover); if (h) heat[s.id] = { v: h.value, lo: h.value, hi: h.value }; }
  const ob = observedBare(cal), seen = strategies.find((s) => s.detected ?? s.is_baseline);
  if (ob && seen) bare[seen.id] = { v: ob.value, lo: ob.value, hi: ob.value };
  return { heat, bare, bareYears: ob?.years ?? [] };
}
export const HEAT_NOTE = `Hot days = NOAA weather-station highs of ${HOT_F} °F or more, in months the rotation leaves the field bare.`;

const WEATHER = WEATHER_LABEL;
type Verdict = 'better' | 'worse' | 'unclear' | 'same' | 'none';
interface N { v: number | null; lo: number | null; hi: number | null; rf?: boolean }
/** Per-field context the metrics need: hot days on bare soil per rotation, from NOAA station highs. */
interface Ctx { heat: Record<string, N>; bare: Record<string, N>; bareYears: number[] }
interface Metric { key: string; label: string; unit: 'af' | 'days' | 'score'; higherIsBetter: boolean; get: (s: RotationStrategy, w: Weather, c: Ctx) => N; gain: string; loss: string }

const n = (x?: SourcedNumber | null): N => (!x || x.blocked || x.value == null ? { v: null, lo: null, hi: null } : { v: x.value, lo: x.low ?? x.value, hi: x.high ?? x.value });
const af = (x: N): N => ({ v: x.v == null ? null : mmToAfac(x.v), lo: x.lo == null ? null : mmToAfac(x.lo), hi: x.hi == null ? null : mmToAfac(x.hi) });
const rep = (s: RotationStrategy, w: Weather, k: 'irrigation_need_mm' | 'exposed_rain_days') => (w === 'typical' ? null : s.exposure.replay[w]?.[k]);

const waterOf = (s: RotationStrategy, w: Weather): N => {
  const x = waterOfAf(s, w);
  return { v: x.v, lo: x.lo, hi: x.hi, rf: x.rf };
};

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

type Market = 'sell' | 'feed' | 'either';
type Focus = 'water' | 'soil' | 'feed' | 'balanced';
const MARKET_API = { sell: 'sell', feed: 'feed_own_herd', either: 'no_preference' } as const;
/** "What matters most" as rotation-model weights (0-4; the rest stay 1). */
const FOCUS_W: Record<Focus, Partial<Record<ScoreKey, number>>> = { water: { water_use: 4 }, soil: { erosion: 3, organic_matter: 3 }, feed: { forage_value: 4 }, balanced: {} };
/** Why the grower's answers rule a rotation out, from the model's own constraint check. */
const whyOut = (s: RotationStrategy) => (s.constraints_check?.some((c) => c.constraint === 'seed_drill' && c.status === 'conflict') ? 'Needs a grain drill' : 'Doesn’t fit your answers');

export default function ComparePanel(p: { loc: Location; strategies: RotationStrategy[]; daily: Daily | null; cal: Calendar | null; live: boolean; allocation: number; exampleLimit: boolean; setAllocation: (v: number) => void; onBrief: (id: string) => void; sim: SimMode; simRunning: boolean; onRunSim: (sim: NonNullable<SimMode>, startT: number) => void; onStopSim: () => void; onClose: () => void; onBack: () => void; onSheet?: (px: number) => void; /** go to step 2, where the water limit is set */ onLimit?: () => void; /** the grower's own current rotation, if they changed it */ todayId?: string | null }) {
  // farmer priorities (0-4) and a rain / temperature what-if, re-scored by the rotation model (POST /score)
  const [weights, setWeights] = useState<Partial<Record<ScoreKey, number>>>({});
  const [scen, setScen] = useState<Scenario>({ dT_c: 0, dP_pct: 0 });
  const [rescored, setRescored] = useState<{ key: string; items: RotationStrategy[] } | null>(null);
  const [busy, setBusy] = useState(false);
  // the grower's three answers: what the crop is for, a grain drill, and what matters most. They go to the rotation
  // model (POST /score): the market answer and the focus re-rank the options, no drill rules out rotations that need one.
  const [market, setMarket] = useState<Market>('either');
  const [drill, setDrill] = useState<'yes' | 'no'>('yes');
  const [focus, setFocus] = useState<Focus>('balanced');
  const answered = market !== 'either' || drill !== 'yes' || focus !== 'balanced';
  const custom = answered || Object.keys(weights).length > 0 || scen.dT_c !== 0 || scen.dP_pct !== 0;
  const key = JSON.stringify([weights, scen, p.allocation, p.loc.id, market, drill, focus]);
  useEffect(() => {
    if (!custom || !p.live) return;
    setBusy(true);
    const base = { ...Object.fromEntries(PRIORITIES.map(([k]) => [k, k === 'pest_break' ? 0 : 1])), market: market === 'either' ? 0 : 2, ...FOCUS_W[focus] };
    const farm = { market_preference: MARKET_API[market], constraints: drill === 'no' ? { has_seed_drill: false } : {} };
    const h = setTimeout(() => scoreStrategies(p.loc.id, p.allocation, { ...base, ...weights }, scen, farm)
      .then((st) => { if (st) setRescored({ key, items: st }); }).finally(() => setBusy(false)), 400);
    return () => clearTimeout(h);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const strategies = custom && rescored?.key === key ? withToday(rescored.items, p.todayId ?? p.strategies.find((x) => x.is_baseline)?.id).map((s) => ({ ...s, water: { ...s.water, etc_vs_openet_pct: p.strategies.find((x) => x.id === s.id)?.water.etc_vs_openet_pct ?? null } })) : p.strategies;
  const ctx = useMemo(() => fieldCtx(strategies, p.daily, p.cal), [strategies, p.daily, p.cal]);
  const flat = useMemo(() => constantScores(strategies), [strategies]);
  const today = strategies.find((s) => s.is_baseline) ?? strategies[0];
  const detail = useDetail().on;
  const allAlts = strategies.filter((s) => s.id !== today.id);
  // best fit first (the model's overall score with the grower's answers); rotations their answers rule out go last
  const alts = [...allAlts].sort((a, b) => Number(!!a.filtered_out) - Number(!!b.filtered_out) || b.composite.value - a.composite.value);
  const avail = alts.filter((s) => !s.filtered_out);
  const [id, setId] = useState<string | null>(null);
  const [weather, setWeather] = useState<Weather>('typical');
  const picked = avail.find((s) => s.id === id) ?? avail[0] ?? null;
  const noneLeft = !picked;
  const alt = picked ?? today;
  const heavy = p.loc.soil.hydrologic_group === 'D';
  const label = (m: Metric) => (m.key === 'infiltration' && heavy ? { ...m, gain: `${m.gain} (small effect on this heavy, slow-draining soil)`, loss: `${m.loss} (small effect on this heavy soil)` } : m);
  const all = detail ? [...UNIT, ...SCORE.filter((m) => !flat.has(m.key)).map(label)] : UNIT;
  const rows = useMemo(() => all.map((m) => { const a = m.get(alt, weather, ctx), b = m.get(today, weather, ctx); return { m, a, b, v: verdict(a, b, m.higherIsBetter) }; }), [alt, today, weather, ctx, flat, detail]); // eslint-disable-line react-hooks/exhaustive-deps
  const gains = rows.filter((r) => r.v === 'better'), losses = rows.filter((r) => r.v === 'worse');
  const unclear = rows.filter((r) => r.v === 'unclear' || r.v === 'same'), none = rows.filter((r) => r.v === 'none');
  const water = (s: RotationStrategy) => waterOf(s, weather);
  const fits = (s: RotationStrategy) => fitsLimit(s, weather, p.allocation);
  const wLabels = weatherLabels(p.loc);
  const scenario = scenarioBlurb(p.loc, weather, alt);
  const ranked = [...strategies].sort((a, b) => b.composite.value - a.composite.value);
  const tie = ranked.length > 1 && (ranked[0].composite.low ?? 0) <= (ranked[1].composite.high ?? 0);

  const fitTone = (s: RotationStrategy) => { const f = fits(s); return f === 'Fits your limit' ? 'good' : f === 'Over your limit' ? 'warn' : 'maybe'; };
  const wa = water(alt), wt = water(today);
  const lim = `${p.allocation.toFixed(1)}${p.exampleLimit ? ' (example)' : ''}`;
  const short = (r: (typeof rows)[number], k: 'gain' | 'loss') => <li key={r.m.key}><b>{r.m[k]}</b><span>{delta(r.m, r.a, r.b)}</span></li>;
  return (
    <StepShell id="compare" testid="compare" resetKey={p.loc.id} onSheet={p.onSheet} onClose={p.onClose} onBack={p.onBack}
      field={<><b>{fieldName(p.loc)}</b> · your rotation now: {rotName(today)}</>}
      title="Which rotation would fit your water?"
      answer={noneLeft ? <Answer tone="warn" headline="No other rotation fits your answers here." sub={drill === 'no' ? 'Every option on this field needs a grain drill. Hiring one, or a custom seeding service, would bring them back.' : 'Change an answer below to see the options again.'} /> : <Answer speak={`${alt.short_name} ${fits(alt) === 'Fits your limit' ? 'fits the water you can get' : fits(alt) === 'Over your limit' ? 'needs more water than you can get' : 'may need more water than you can get'}. ${scenario}`} tone={fitTone(alt) === 'good' ? 'good' : fitTone(alt) === 'warn' ? 'warn' : 'neutral'}
        headline={`${alt.short_name} ${fits(alt) === 'Fits your limit' ? 'fits the water you can get' : fits(alt) === 'Over your limit' ? 'needs more water than you can get' : 'may need more water than you can get'}.`}
        sub={<>{wa.rf ? `${alt.short_name} is ${RAIN_FED.toLowerCase()}.` : `${alt.short_name} needs about ${wa.v?.toFixed(1)} acre-ft per acre a year.`} Your current rotation, {rotName(today)}, needs {wt.rf ? 'no irrigation' : `${wt.v?.toFixed(1)}`}. You can get {lim}.</>} />}
      next={{ label: 'Next: print for your adviser', sub: noneLeft ? 'One page on what you grow today' : `One page on ${alt.short_name.toLowerCase()}`, onClick: () => p.onBrief(alt.id), testid: 'to-brief' }}
      detailWhat="Every factor, priorities, play a year on the map"
      detail={<>
        <h2 className="fp-h">Water against your limit <What k="waterBalance" /></h2>
        <p className="how">{rng(UNIT[0], wa) ? `${rng(UNIT[0], wa).replace(/^likely/, 'Likely')} acre-ft/acre, ` : ''}{WEATHER[weather].toLowerCase()}.{/safflower|wheat/i.test(alt.name) ? ' An upper bound: soil water stored over winter is not counted.' : ''} {openetText(p.strategies)}</p>
        <h2 className="fp-h">Bare days <What k="bare" /></h2>
        <p className="how">Today: {ctx.bare[today.id]?.v != null ? `${ctx.bare[today.id].v} days a year, seen by satellite ${ctx.bareYears[0]}–${ctx.bareYears[ctx.bareYears.length - 1]}` : `${Math.round(today.exposure.bare_days_per_year.value)} days a year (estimated)`}. Other rotations: estimated by the rotation model. {BARE_DEF}</p>
        <h2 className="fp-h">Every option, every factor</h2>
        <div className="c1-body scroll-x">
          <table className="tt">
            <thead><tr><th /><th className="today">Today<small>{today.short_name}</small></th>{allAlts.map((s) => <th key={s.id}>Option<small>{s.short_name}</small></th>)}</tr></thead>
            <tbody>
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
        <h2 className="fp-h">What matters to you</h2>
        <div className="c2-tune stacked" data-testid="tune-panel">
          {PRIORITIES.map(([k, lab]) => {
            const v = weights[k] ?? (k === 'pest_break' ? 0 : 1);
            return <div key={k} className="pri-row"><span>{lab}</span><Seg className="small" label={lab} value={v} onChange={(i) => setWeights({ ...weights, [k]: i })} options={LEVEL.map((l, i) => ({ v: i, label: l, disabled: !p.live }))} /></div>;
          })}
          <h4>What if the year is</h4>
          <Seg className="small" label="Rain" value={scen.dP_pct} onChange={(v) => setScen({ ...scen, dP_pct: v })} options={RAIN.map(([v, l]) => ({ v, label: l, disabled: !p.live, testid: `rain-${v}` }))} />
          <Seg className="small" label="Heat" value={scen.dT_c} onChange={(v) => setScen({ ...scen, dT_c: v })} options={HEAT.map(([v, l]) => ({ v, label: l, disabled: !p.live }))} />
          <p className="how">{!p.live ? 'Needs the CropLytics server; showing the saved scores.' : busy ? 'Re-scoring…' : custom ? 'Water need and ranking use your settings.' : 'Default: every priority counts the same, normal weather.'}</p>
          <h4>Best fit for what matters to you</h4>
          <ol className="rank">{ranked.map((s, i) => <li key={s.id} className={s.is_baseline ? 'base' : ''}>{s.short_name}{s.is_baseline ? ' (today)' : ''}{i === 0 && tie ? <small> too close to call with the next one</small> : null}</li>)}</ol>
        </div>
        <SimRun loc={p.loc} strategies={p.strategies} allocation={p.allocation} pickId={alt.id} weather={weather} onRun={p.onRunSim} running={p.simRunning} onStop={p.onStopSim} />
        <p className="how">Better / worse = the whole likely range is above or below today’s. Water need: rotation model with NASA POWER weather, 2015–2025. {p.loc.region === 'bc' ? HEAT_NOTE.replace('NOAA', 'Environment Canada') : HEAT_NOTE} Supports, doesn’t replace, your adviser.</p>
      </>}>
      <div className="farm-q" data-testid="farm-questions">
        <Choice testid="q-market" label="What will you do with the crop?" value={market} onChange={setMarket} disabled={!p.live}
          options={[{ v: 'sell', label: 'Sell it' }, { v: 'feed', label: 'Feed my own herd' }, { v: 'either', label: 'Either' }]} />
        <Choice testid="q-drill" label="Do you have a grain drill?" hint="Small grains and safflower are drilled." value={drill} onChange={setDrill} disabled={!p.live}
          options={[{ v: 'yes', label: 'Yes, or I can hire one' }, { v: 'no', label: 'No' }]} />
        <Choice testid="q-focus" label="What matters most to you?" value={focus} onChange={setFocus} disabled={!p.live}
          options={[{ v: 'water', label: 'Saving water' }, { v: 'soil', label: 'Healthy soil' }, { v: 'feed', label: 'More feed' }, { v: 'balanced', label: 'All about equal' }]} />
        {!p.live && <p className="how">Needs the CropLytics server to re-rank the options.</p>}
      </div>
      <h2 className="fp-h opt-h">{answered ? 'Best fit for your answers' : 'Options for this field'}{busy && <small className="muted"> Updating…</small>}</h2>
      <div className="opt-today" data-testid="opt-today">
        <span className="opt-body"><small>Your rotation now</small><b>{today.short_name.replace(/\s*\(current\)$/i, '')}</b>
          <span className="month-strip" aria-hidden="true">{today.month_cover.split('').map((c, m) => <i key={m} title={today.calendar_months[m]} style={{ background: CLASS_COLOR[c as CoverClass] }} />)}</span></span>
        <span className={`opt-fit ${fitTone(today)}`}><b>{wt.rf ? 'Rain-fed' : wt.v?.toFixed(1)}</b><small>{wt.rf || fitTone(today) === 'good' ? 'fits' : fitTone(today) === 'warn' ? 'over' : 'may go over'}</small></span>
      </div>
      <div className={`opt-list ${busy ? 'busy' : ''}`} role="radiogroup" aria-label="Rotation to compare with today" aria-busy={busy}>
        {alts.map((s, i) => {
          const w = water(s), on = !noneLeft && s.id === alt.id, tone = fitTone(s), out = !!s.filtered_out;
          return (
            <button key={s.id} role="radio" aria-checked={on} disabled={out} className={`opt-row ${on ? 'on' : ''} ${out ? 'out' : ''}`} onClick={() => setId(s.id)} data-alt={s.id}>
              <span className="opt-radio" aria-hidden="true" />
              <span className="opt-body">
                <b>{s.short_name}{i === 0 && !out && <em className="opt-best">{answered ? 'Best fit for you' : 'Top pick'}</em>}</b>
                {out ? <small>{whyOut(s)}</small> : <span className="month-strip" aria-hidden="true">{s.month_cover.split('').map((c, m) => <i key={m} title={s.calendar_months[m]} style={{ background: CLASS_COLOR[c as CoverClass] }} />)}</span>}
              </span>
              {!out && <span className={`opt-fit ${tone}`}><b>{w.rf ? 'Rain-fed' : `${w.v?.toFixed(1)}`}</b><small>{w.rf ? 'fits' : tone === 'good' ? 'fits' : tone === 'warn' ? 'over' : 'may go over'}</small></span>}
            </button>
          );
        })}
      </div>
      <div className="limit-line">
        <span>Water you can get <b>{p.allocation.toFixed(1)} acre-ft per acre a year</b>{p.exampleLimit && <em className="status example ex-limit">example</em>}</span>
        {p.onLimit && <button className="btn btn-text btn-sm" onClick={p.onLimit} data-testid="change-limit">Change</button>}
      </div>
      <WaterBars strategies={strategies} selId={alt.id} todayId={today.id} weather={weather} allocation={p.allocation} acres={fieldAcres(p.loc)} />
      <p className="how scenario-sum" data-testid="scenario-summary" key={weather} role="status">{scenario}</p>
      {!noneLeft && <div className="gl-short">
        <div><h3 className="gain">You gain</h3>{gains.length ? <ul>{gains.slice(0, 3).map((r) => short(r, 'gain'))}</ul> : <p className="muted">Nothing clearly better than today.</p>}</div>
        <div><h3 className="loss">You give up</h3>{losses.length ? <ul>{losses.slice(0, 3).map((r) => short(r, 'loss'))}</ul> : <p className="muted">Nothing clearly worse than today.</p>}</div>
      </div>}
    </StepShell>
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
