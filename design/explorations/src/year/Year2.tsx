// Option 2 — ten years stacked so the repeating pattern jumps out; one risk at a time; click a year for its story.
import { useState } from 'react';
import { ALL_RAIN, ALL_RAIN_HIT, CAL, CLS, Cls, MONTHS, MONTH_START, RICE_YEARS, RISK, Risk, TYPICAL, YEARS, approxDoy, classAt, cropOf, daysIn, eventsIn, fmtDate, newsIn, simple, yearFacts } from '../data';
import { Detector, Legend } from '../ui';
import { headline } from './Year1';

const fill = (c: Cls) => (c === 'unknown' ? 'url(#hatch2)' : CLS[c].color);

function Strip({ segs, n }: { segs: { s: number; e: number; c: Cls }[]; n: number }) {
  return (
    <svg className="strip" viewBox={`0 0 ${n} 10`} preserveAspectRatio="none">
      <defs>
        <pattern id="hatch2" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="3" fill="#4b5260" /><rect width="1.2" height="3" fill="#7b818c" /></pattern>
      </defs>
      {segs.map((g, i) => <rect key={i} x={g.s - 1} width={g.e - g.s + 1} height={10} fill={fill(g.c)} />)}
    </svg>
  );
}

/** Most common simple class per day across rice years. */
const typicalSegs = (() => {
  const out: { s: number; e: number; c: Cls }[] = [];
  for (let d = 1; d <= 365; d++) {
    const n: Record<string, number> = {};
    RICE_YEARS.forEach((y) => { const c = simple(classAt(y, d)); n[c] = (n[c] ?? 0) + 1; });
    const c = Object.entries(n).sort((a, b) => b[1] - a[1])[0][0] as Cls;
    if (out.length && out[out.length - 1].c === c) out[out.length - 1].e = d; else out.push({ s: d, e: d, c });
  }
  return out;
})();

export default function Year2({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const [risk, setRisk] = useState<Risk>('rain');
  const [detail, setDetail] = useState(false);
  const cls = (c: string) => (detail ? (c as Cls) : simple(c as Cls));
  const fallow = YEARS.filter((y) => cropOf(y) !== 'Rice');
  const maxExposed = 366;
  return (
    <section className="panel glass wide y2">
      <header className="ph">
        <h1>Is your field bare at the same time every year, and does bad weather land then?</h1>
        <p className="headline">
          In rice years the crop covers the field from about {approxDoy(TYPICAL.start)} to {approxDoy(TYPICAL.end)}; the other eight months it is bare, thin or flooded.
          Fallow years ({fallow.join(', ')}) stayed bare almost all year. Since 2016, <b>{ALL_RAIN_HIT.length} of {ALL_RAIN.length}</b> heavy-rain days landed on bare or thin ground.
        </p>
      </header>
      <div className="y2-controls">
        <div className="seg">
          {(['rain', 'heat', 'frost'] as Risk[]).map((t) => (
            <button key={t} className={risk === t ? 'on' : ''} onClick={() => setRisk(t)}><i className="dot" style={{ background: RISK[t].color }} />{RISK[t].label}</button>
          ))}
        </div>
        <small className="muted">{RISK[risk].rule}</small>
        <span className="grow" />
        <Legend classes={detail ? ['bare', 'partial', 'covered', 'water', 'unknown'] : ['bare', 'covered', 'water', 'unknown']} simpleView={!detail} />
        <button className="link" onClick={() => setDetail(!detail)}>{detail ? 'Simpler colours' : 'Split bare / thin'}</button>
      </div>

      <div className="y2-grid">
        <div className="y2-row head">
          <span />
          <div className="months">{MONTH_START(2021).map((d, m) => <span key={m} style={{ left: `${((d - 1) / 365) * 100}%` }}>{MONTHS[m]}</span>)}</div>
          <span className="col-h">Days bare or thin</span>
          <span className="col-h">{RISK[risk].label} on bare</span>
        </div>
        <div className="y2-row typical">
          <span className="yl"><b>Typical rice year</b><small>most common, {RICE_YEARS.length} rice years</small></span>
          <div className="cell"><Strip segs={typicalSegs} n={365} /></div>
          <span className="num">{TYPICAL.exposedAvg}</span>
          <span />
        </div>
        {CAL.map((yc) => {
          const f = yearFacts(yc.year);
          const ev = eventsIn(yc.year, risk);
          const n = daysIn(yc.year);
          const hit = ev.filter((e) => e.exposed).length;
          return (
            <button key={yc.year} className={`y2-row ${yc.year === year ? 'sel' : ''}`} onClick={() => setYear(yc.year)}>
              <span className="yl"><b>{yc.year}</b><small className={f.crop === 'Rice' ? '' : 'fallow'}>{f.crop}</small></span>
              <div className="cell">
                <Strip segs={yc.segments.map((s) => ({ s: s.start_doy, e: s.end_doy, c: cls(s.class) }))} n={n} />
                {ev.map((e, i) => (
                  <i key={i} className={`ev ${e.exposed ? 'hit' : ''}`} style={{ left: `${((e.doy - 0.5) / n) * 100}%`, color: RISK[risk].color }} title={`${fmtDate(e.date)}: ${e.value} ${RISK[risk].unit}, field ${CLS[e.cls].label.toLowerCase()}`} />
                ))}
                {detail && yc.markers.map((m, i) => (
                  <i key={'m' + i} className={`mk ${m.type}`} style={{ left: `${(((+new Date(m.date) - Date.UTC(yc.year, 0, 1)) / 864e5) / n) * 100}%` }} title={m.type === 'green_up' ? 'Green-up' : 'Harvest / die-back'} />
                ))}
              </div>
              <span className="num"><i style={{ width: `${(f.exposedDays / maxExposed) * 100}%` }} />{f.exposedDays}</span>
              <span className="num2">{hit ? <b style={{ color: RISK[risk].color }}>{hit}</b> : <small>0</small>}<small> / {ev.length}</small></span>
            </button>
          );
        })}
        <div className="y2-keys">
          <span><i className="ev hit" style={{ color: RISK[risk].color }} /> landed on bare or thin ground</span>
          <span><i className="ev" style={{ color: RISK[risk].color }} /> field was covered or flooded (protected)</span>
          {detail && <span><i className="mk green_up" /> green-up <i className="mk senescence_harvest" /> harvest / die-back</span>}
        </div>
      </div>

      <div className="y2-foot">
        <div className="callout">
          <b>{year}</b> {headline(year).replace(`${year}: `, '')}
          {newsIn(year).slice(0, 2).map((n) => <a key={n.url} href={n.url} target="_blank" rel="noreferrer" className="inline-news">“{n.title}” <small>{n.source}, {fmtDate(n.date)}</small></a>)}
        </div>
        <Detector compact />
      </div>
    </section>
  );
}
