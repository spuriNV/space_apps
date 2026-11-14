// Option 1 — a trade-off table in words. No winner is picked; each cell says Better / Worse / Can't tell vs today.
import { useState } from 'react';
import { ALTS, DEFAULT_W, Num, PLAIN, SHORT, STRATS, TODAY, mmAf, overall, overlapShare, r0, verdict } from '../data';
import { AssumedNote, VerdictChip } from '../ui';
import { EXTRA_METRICS, Metric, SCORE_METRICS, UNIT_METRICS, Weather, WEATHER_LABEL, rangeText } from './common';

function Row({ m, w }: { m: Metric; w: Weather }) {
  const base = m.get(TODAY, w);
  const short = m.unit === 'score';
  const txt = (n: Num) => (short ? (n.v == null ? '' : `${r0(n.v)}${n.lo != null && n.hi != null && Math.round(n.lo) !== Math.round(n.hi) ? ` (${r0(n.lo)}–${r0(n.hi)})` : ''}`) : rangeText(n, m.fmt));
  return (
    <tr className={short ? 'short' : ''}>
      <th>{m.label}</th>
      <td className="today">{txt(base)}</td>
      {ALTS.map((s) => {
        const n = m.get(s, w);
        return (
          <td key={s.id}>
            <VerdictChip v={verdict(n, base, m.higherIsBetter)} />
            <small>{txt(n)}</small>
          </td>
        );
      })}
    </tr>
  );
}

export default function Compare1({ weather }: { weather: Weather }) {
  const [more, setMore] = useState(false);
  const o = (s: (typeof STRATS)[number]) => overall(s, DEFAULT_W);
  const ot = o(TODAY);
  const saff = ALTS.find((s) => s.id === 'car2_dryyear_safflower')!;
  const dWater = TODAY.water.irrigation_need_mm.v! - saff.water.irrigation_need_mm.v!;
  const dBare = saff.exposure.bare_days_per_year.v! - TODAY.exposure.bare_days_per_year.v!;
  return (
    <section className="panel glass wide c1">
      <header className="ph row">
        <div>
          <h1>What changes if you farm this field differently?</h1>
          <p className="headline">
            All three alternatives come out ahead of today on the brief’s six priorities, but they are <b>too close to call</b> against each other.
            The real choice is a trade: dry-year safflower needs about {r0(dWater)} mm ({mmAf(dWater)}) less water a year, but leaves the field bare about {r0(dBare)} more days.
          </p>
        </div>
        <AssumedNote />
      </header>
      <div className="c1-body">
        <table className="tt">
          <thead>
            <tr>
              <th />
              <th className="today" title={PLAIN[TODAY.id]}><span className="tag">What you do now</span>Rice, winter flood</th>
              {ALTS.map((s) => <th key={s.id} title={PLAIN[s.id]}><span className="tag alt">Alternative</span>{SHORT[s.id]}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr className="grp"><td colSpan={5}>In real units · {WEATHER_LABEL[weather].toLowerCase()}</td></tr>
            {UNIT_METRICS.map((m) => <Row key={m.key} m={m} w={weather} />)}
            <tr className="grp"><td colSpan={5}>The brief’s six priorities · score out of 100, higher is better</td></tr>
            {SCORE_METRICS.map((m) => <Row key={m.key} m={m} w={weather} />)}
            {more && EXTRA_METRICS.map((m) => <Row key={m.key} m={m} w={weather} />)}
            <tr className="more"><td colSpan={5}><button className="link" onClick={() => setMore(!more)}>{more ? 'Hide the 4 extra factors' : 'Show 4 extra factors (pest break, soil structure, winter nitrogen, income)'}</button></td></tr>
            <tr className="overall">
              <th>Overall, six priorities weighted equally</th>
              <td className="today">{r0(ot.v)} <small>likely {r0(ot.lo)}–{r0(ot.hi)}</small></td>
              {ALTS.map((s) => {
                const os = o(s);
                const ties = ALTS.filter((t) => t.id !== s.id && overlapShare([os.lo, os.hi], [o(t).lo, o(t).hi]) > 0.5);
                return (
                  <td key={s.id}>
                    {overlapShare([os.lo, os.hi], [ot.lo, ot.hi]) > 0.5 ? <VerdictChip v="unclear">Too close to call with today</VerdictChip> : <VerdictChip v={os.v > ot.v ? 'better' : 'worse'}>{os.v > ot.v ? 'Ahead of today' : 'Behind today'}</VerdictChip>}
                    {ties.length > 0 && <span className="vchip v-tie">≈ Too close to call with {ties.map((t) => SHORT[t.id]).join(' and ')}</span>}
                    <small>{r0(os.v)}, likely {r0(os.lo)}–{r0(os.hi)}</small>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
        <aside className="howto">
          <h3>How to read this</h3>
          <p><VerdictChip v="better" /> / <VerdictChip v="worse" /> the alternative’s whole range of likely values is above / below today’s.</p>
          <p><VerdictChip v="unclear" /> the ranges overlap. Our inputs aren’t precise enough to say which is better.</p>
          <p><b>Why a range, not one number?</b> We don’t know some inputs exactly: how thirsty the crop is, which rain record is right, where “bare” starts. So we run the low and high cases and show both: “likely 1,315–2,047”.</p>
          <p><b>Too close to call</b> means two options’ overall ranges overlap by more than half. Treat them as equal and decide on what matters to you.</p>
          <p className="muted">Income and insurance-loss history are not scored yet (no price data). Rules of thumb, not a farm model: it supports, doesn’t replace, your adviser.</p>
        </aside>
      </div>
    </section>
  );
}
