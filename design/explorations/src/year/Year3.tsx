// Option 3 — a three-chapter story: a normal year, then the 2022 drought and the 2023 storms, each against the normal year.
import { CLS, Cls, MONTHS, MONTH_START, RISK, Risk, daysIn, eventsIn, fmtDate, newsIn, simple, yearCal, yearFacts } from '../data';
import { Detector, Legend } from '../ui';

const NORMAL = 2024;
const CHAPTERS = [
  { year: NORMAL, title: 'A normal rice year', line: 'Flooded in winter, bare in spring, rice all summer.' },
  { year: 2022, title: 'The 2022 drought', line: 'Water was cut; no rice was planted. The field sat bare.' },
  { year: 2023, title: 'The 2023 storms', line: 'Atmospheric rivers in Jan–Mar; rice went in late.' },
];

interface Note { doy: number; text: string; kind: 'cover' | 'risk' | 'news' }
function notes(y: number): Note[] {
  const out: Note[] = [];
  const yc = yearCal(y);
  yc.segments.filter((s) => s.class === 'water' && s.days >= 7).forEach((s) => out.push({ doy: s.start_doy, text: `Flooded ${s.days} days`, kind: 'cover' }));
  yc.markers.forEach((m) => {
    const d = Math.round((+new Date(m.date) - Date.UTC(y, 0, 1)) / 864e5) + 1;
    if (m.type === 'green_up' && d > 120) out.push({ doy: d, text: `Rice greens up, ${fmtDate(m.date)}`, kind: 'cover' });
    if (m.type === 'senescence_harvest' && d > 200 && d < 300) out.push({ doy: d, text: `Harvest, ${fmtDate(m.date)}`, kind: 'cover' });
  });
  if (!yc.markers.length) out.push({ doy: 160, text: 'No crop all year', kind: 'cover' });
  (['rain', 'heat'] as Risk[]).forEach((t) => {
    const hit = eventsIn(y, t).filter((e) => e.exposed);
    if (hit.length) out.push({ doy: hit[Math.floor(hit.length / 2)].doy, text: `${hit.length} ${RISK[t].label.toLowerCase()} days on bare soil`, kind: 'risk' });
  });
  return out.sort((a, b) => a.doy - b.doy);
}

function Strip({ y, h, simpleView = true }: { y: number; h: number; simpleView?: boolean }) {
  const n = daysIn(y);
  return (
    <svg className="strip" style={{ height: h }} viewBox={`0 0 ${n} 10`} preserveAspectRatio="none">
      {yearCal(y).segments.map((s, i) => {
        const c = simpleView ? simple(s.class as Cls) : (s.class as Cls);
        return <rect key={i} x={s.start_doy - 1} width={s.days} height={10} fill={CLS[c].color} />;
      })}
    </svg>
  );
}

export default function Year3({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const ch = CHAPTERS.find((c) => c.year === year) ?? CHAPTERS[1];
  const y = ch.year;
  const n = daysIn(y);
  const f = yearFacts(y), base = yearFacts(NORMAL);
  const pct = (doy: number, nn = n) => `${((doy - 0.5) / nn) * 100}%`;
  const ns = notes(y);
  const isNormal = y === NORMAL;
  const tiles = [
    { label: 'Days bare or thin', v: f.exposedDays, b: base.exposedDays, unit: 'days' },
    { label: 'Extreme heat on bare soil', v: f.heatHit.length, b: base.heatHit.length, unit: 'days ≥ 40 °C (104 °F)' },
    { label: 'Heavy rain on bare soil', v: f.rainHit.length, b: base.rainHit.length, unit: 'days ≥ 25 mm (1 in)' },
    { label: 'Flooded', v: f.days.water, b: base.days.water, unit: 'days' },
  ];
  return (
    <section className="panel glass wide y3">
      <header className="ph">
        <h1>What happened to your field in the drought and the floods?</h1>
        <p className="headline">
          In a normal year the field is bare or thin about {base.exposedDays} days. In the 2022 drought that rose to {yearFacts(2022).exposedDays}, with {yearFacts(2022).heatHit.length} days over 40 °C (104 °F) on bare soil.
          In the 2023 storms it was mostly flooded or thinly covered when the heavy rain came.
        </p>
      </header>
      <div className="y3-body">
        <ol className="chapters">
          {CHAPTERS.map((c, i) => (
            <li key={c.year}>
              <button className={c.year === y ? 'on' : ''} onClick={() => setYear(c.year)} data-chapter={c.year}>
                <span className="ch-n">{i + 1}</span>
                <span><b>{c.title}</b><small>{c.line}</small></span>
              </button>
            </li>
          ))}
          <li className="ch-hint muted">Each chapter is shown against the normal year, so you only read what changed.</li>
        </ol>

        <div className="y3-main">
          <div className="y3-axis">{MONTH_START(y).map((d, m) => <span key={m} style={{ left: pct(d) }}>{MONTHS[m]}</span>)}</div>
          {!isNormal && (
            <div className="y3-ref">
              <span>Normal year ({NORMAL})</span>
              <Strip y={NORMAL} h={14} />
            </div>
          )}
          <div className="y3-notes">
            {ns.map((m, i) => (
              <div key={i} className={`note ${m.kind} lvl${i % 2} ${m.doy > n * 0.7 ? 'right' : ''}`} style={{ left: pct(m.doy) }}><span>{m.text}</span></div>
            ))}
          </div>
          <div className="y3-big">
            <span className="y3-yl"><b>{y}</b><small>{f.crop}</small></span>
            <div className="y3-strip">
              <Strip y={y} h={56} />
              {(['rain', 'heat', 'frost'] as Risk[]).flatMap((t) => eventsIn(y, t).map((e, i) => (
                <i key={t + i} className={`ev2 ${e.exposed ? 'hit' : ''} ${t}`} style={{ left: pct(e.doy), color: RISK[t].color }} title={`${fmtDate(e.date)}: ${RISK[t].label} ${e.value} ${RISK[t].unit}`} />
              )))}
            </div>
          </div>
          <div className="y3-keys">
            <Legend classes={['bare', 'covered', 'water']} simpleView />
            <span className="legend">
              {(['rain', 'heat', 'frost'] as Risk[]).map((t) => <span key={t}><b className="dot" style={{ background: RISK[t].color }} />{RISK[t].label} <small>({RISK[t].rule})</small></span>)}
              <span><b className="dot hollow" />hollow = field was protected</span>
            </span>
          </div>
          <div className="y3-news">
            {newsIn(y).filter((_, i, a) => a.length <= 4 || i % 2 === 0).slice(0, 4).map((nn) => (
              <a key={nn.url} href={nn.url} target="_blank" rel="noreferrer" className="news">
                <small>{fmtDate(nn.date)} · {nn.source}</small>{nn.title}
              </a>
            ))}
            {!newsIn(y).length && <p className="muted">Nothing went wrong this year, so there is little to report. Use it as the yardstick.</p>}
          </div>
          <div className="tiles">
            {tiles.map((t) => (
              <div key={t.label} className="tile">
                <small>{t.label}</small>
                <b>{t.v}</b> <span className="muted">{t.unit}</span>
                {!isNormal && <em className={t.v > t.b ? 'up' : t.v < t.b ? 'down' : ''}>normal year: {t.b}</em>}
              </div>
            ))}
          </div>
          <Detector compact />
        </div>
      </div>
    </section>
  );
}
