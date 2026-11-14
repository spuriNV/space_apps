// Option 1 — one year as a clock face: you read it like a calendar wall chart, Jan at the top.
import { CLS, Cls, MONTHS, MONTH_START, RISK, Risk, approxDoy, daysIn, eventsIn, fmtDate, newsIn, yearCal, yearFacts } from '../data';
import { Detector, Legend } from '../ui';

const R0 = 118, R1 = 170, C = 240;
function arc(a0: number, a1: number, r0: number, r1: number) {
  const p = (a: number, r: number) => `${C + r * Math.cos(a)},${C + r * Math.sin(a)}`;
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${p(a0, r1)} A${r1},${r1} 0 ${large} 1 ${p(a1, r1)} L${p(a1, r0)} A${r0},${r0} 0 ${large} 0 ${p(a0, r0)} Z`;
}

export function mainCover(y: number) {
  return yearCal(y).segments.filter((s) => s.class === 'covered' && s.start_doy > 120).sort((a, b) => b.days - a.days)[0];
}
export function headline(y: number) {
  const f = yearFacts(y);
  const cov = mainCover(y);
  if (!cov) return `${y}: no crop on record. The field sat bare or thin for ${f.exposedDays} days; ${f.heatHit.length} extreme-heat days and ${f.rainHit.length} heavy-rain days hit bare ground.`;
  return `${y}: rice covered the field from ${approxDoy(cov.start_doy, y)} to ${approxDoy(cov.end_doy, y)}. It was bare or thin for ${f.exposedDays} days, and ${f.rainHit.length} of ${f.rain.length} heavy-rain days landed then.`;
}

export default function Year1({ year }: { year: number }) {
  const N = daysIn(year);
  const ang = (doy: number) => ((doy - 1) / N) * 2 * Math.PI - Math.PI / 2;
  const f = yearFacts(year);
  const ms = MONTH_START(year);
  const ring: Record<Risk, number> = { rain: R1 + 14, heat: R1 + 26, frost: R1 + 38 };
  return (
    <section className="panel glass y1">
      <header className="ph">
        <h1>When is your field bare, and what hit it then?</h1>
        <p className="headline">{headline(year)}</p>
      </header>
      <div className="y1-body">
        <div className="y1-ring">
          <svg width={480} height={480}>
            {yearCal(year).segments.map((s, i) => (
              <path key={i} d={arc(ang(s.start_doy), ang(s.end_doy + 1), R0, R1)} fill={s.class === 'unknown' ? 'url(#hatch)' : CLS[s.class as Cls].color} />
            ))}
            <defs>
              <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" fill="#4b5260" /><rect width="2.5" height="6" fill="#7b818c" />
              </pattern>
            </defs>
            {ms.map((d, m) => {
              const a = ang(d), am = ang(d + 15);
              return (
                <g key={m}>
                  <line x1={C + (R0 - 4) * Math.cos(a)} y1={C + (R0 - 4) * Math.sin(a)} x2={C + (R1 + 4) * Math.cos(a)} y2={C + (R1 + 4) * Math.sin(a)} stroke="#0d1218" strokeWidth={1.5} />
                  <text x={C + (R1 + 54) * Math.cos(am)} y={C + (R1 + 54) * Math.sin(am)} className="ring-month" textAnchor="middle" dominantBaseline="middle">{MONTHS[m]}</text>
                </g>
              );
            })}
            {(Object.keys(ring) as Risk[]).map((t) =>
              eventsIn(year, t).map((e, i) => {
                const a = ang(e.doy) + (0.5 / N) * 2 * Math.PI;
                return <circle key={t + i} cx={C + ring[t] * Math.cos(a)} cy={C + ring[t] * Math.sin(a)} r={e.exposed ? 4.2 : 3.2} fill={e.exposed ? RISK[t].color : 'none'} stroke={RISK[t].color} strokeOpacity={e.exposed ? 1 : 0.5} strokeWidth={1.3}><title>{`${fmtDate(e.date)}: ${RISK[t].label} ${e.value} ${RISK[t].unit} — field: ${CLS[e.cls].label}`}</title></circle>;
              }),
            )}
            <text x={C} y={C - 30} textAnchor="middle" className="ring-year">{year}</text>
            <text x={C} y={C - 4} textAnchor="middle" className="ring-crop">{f.crop}</text>
            <text x={C} y={C + 28} textAnchor="middle" className="ring-big">{f.exposedDays} days</text>
            <text x={C} y={C + 46} textAnchor="middle" className="ring-sub">bare or thin</text>
          </svg>
          <Legend classes={['bare', 'partial', 'covered', 'water', 'unknown']} />
          <div className="legend">
            <span><b className="dot" style={{ background: '#ccc' }} />filled dot = hit bare/thin ground</span>
            <span><b className="dot hollow" />hollow = field was covered or flooded</span>
          </div>
        </div>
        <div className="y1-side">
          <h3>What hit it while it was bare</h3>
          {(['rain', 'heat', 'frost'] as Risk[]).map((t) => {
            const all = eventsIn(year, t);
            const hit = all.filter((e) => e.exposed);
            return (
              <div key={t} className="hit-row">
                <i className="dot" style={{ background: RISK[t].color }} />
                <div>
                  <b>{RISK[t].label}</b> <small>{RISK[t].rule}</small>
                  <p><strong>{hit.length}</strong> of {all.length} days landed on bare or thin ground
                    {hit.length > 0 && t === 'rain' && <> · {hit.slice(0, 3).map((e) => `${fmtDate(e.date)} (${Math.round(e.value)} mm)`).join(', ')}</>}
                  </p>
                </div>
              </div>
            );
          })}
          <h3>In the news that year</h3>
          {newsIn(year).length ? (
            newsIn(year).slice(0, 3).map((n) => (
              <a key={n.url} className="news" href={n.url} target="_blank" rel="noreferrer"><small>{fmtDate(n.date)} · {n.source}</small>{n.title}</a>
            ))
          ) : (
            <p className="muted">No local headlines collected for {year}. News is gathered for 2022 (drought) and 2023 (storms).</p>
          )}
          <Detector compact />
          <p className="src">Field cover: Sentinel-2 + Landsat, {f.days.unknown} days with no clear view. Weather: NASA POWER daily (~50 km cell).</p>
        </div>
      </div>
    </section>
  );
}
