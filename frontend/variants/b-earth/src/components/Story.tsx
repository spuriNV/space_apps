import type { Calendar, CoverClass, Location, NewsItem, Regional, Story } from '../types';
import { CLASS_COLOR, CLASS_LABEL, dateToT, fieldState, fmtDate, ordinal, tLabel, tOf } from '../lib';
import Icon from './Icons';

export default function StoryPanel(p: { loc: Location; story: Story; idx: number; setIdx: (i: number) => void; cal: Calendar; regional: Regional; news: NewsItem[]; t: number; detector: 'rule' | 'ml'; onClose: () => void }) {
  const ch = p.story.chapters[p.idx];
  const t0 = tOf(p.story.window[0], 0), t1 = tOf(p.story.window[1], 35);
  const W = 348, H = 96, x = (t: number) => ((t - t0) / (t1 - t0)) * W;
  const smap = p.regional.smap_rootzone_pct.values, grace = p.regional.grace_gw_pct.values, rain = p.regional.imerg_mm_dekad.values as number[];
  const line = (vals: (number | null)[]) => { let d = ''; for (let t = t0; t <= t1; t++) { const v = vals[t]; if (v != null) d += `${d ? 'L' : 'M'}${x(t).toFixed(1)},${(H - 4 - (v / 100) * (H - 30)).toFixed(1)}`; } return d; };
  const fs = fieldState(p.cal, p.t, p.detector);
  const live = ch.saw.series === 'smap' ? `${ordinal(smap[p.t] ?? 0)} percentile` : ch.saw.series === 'grace' ? (grace[p.t] == null ? 'no data' : `${ordinal(grace[p.t]!)} percentile`) : ch.saw.series === 'imerg' ? `${rain[p.t]} mm (${(rain[p.t] / 25.4).toFixed(1)} in) in 10 days` : CLASS_LABEL[fs.cls];
  const reported = ch.reported.map((title) => p.news.find((n) => n.title === title)).filter((n): n is NewsItem => !!n);
  const strip = p.cal.years.map((y) => (p.detector === 'rule' ? y.rule : y.ml)).join('');
  return (
    <section className="panel glass story" data-testid="story">
      <header className="panel-head">
        <h2>Story <small>satellite saw vs news reported</small></h2>
        <button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button>
      </header>
      <div className="panel-scroll">
        <div className="st-top">
          <span className="st-kicker">{p.loc.short_name} · {p.story.title}</span>
          <div className="st-steps">
            {p.story.chapters.map((c, i) => <button key={c.date} className={i === p.idx ? 'on' : i < p.idx ? 'done' : ''} onClick={() => p.setIdx(i)} title={c.title} data-testid={`chapter-${i}`}>{i + 1}</button>)}
          </div>
        </div>
        <h3 className="st-title">{ch.title}</h3>
        <div className="st-cols">
          <div className="st-col saw">
            <span className="st-label"><Icon name="sat" size={14} />Satellite saw</span>
            <span className={`badge-scale ${ch.saw.scale === '30 m' ? '' : 'coarse'}`}>{ch.saw.dataset} {ch.saw.scale}</span>
            <p>{ch.saw.text}</p>
            <b className="st-live">{tLabel(p.t)}: {live}</b>
          </div>
          <div className="st-col news">
            <span className="st-label"><Icon name="news" size={14} />News reported</span>
            {reported.length === 0 && <p className="muted">No headline in the cached news for this date. The signal came first.</p>}
            {reported.map((n) => (
              <a key={n.title} href={n.url ?? undefined} target="_blank" rel="noreferrer" className="st-news">
                <small>{fmtDate(n.date)} · {n.source}{n.verified ? '' : ' · unverified'}</small>
                <b>{n.title}</b>
              </a>
            ))}
            <span className="chip tiny">Lead time: computing</span>
          </div>
        </div>
        <div className="st-chart">
          <div className="st-chart-key">
            <span><i style={{ background: '#5ab0ff' }} />Soil moisture pct. (SMAP)</span>
            <span><i style={{ background: '#ff7eb6' }} />Groundwater pct. (GRACE)</span>
            <span><i style={{ background: '#9d8cff' }} />Rain (IMERG)</span>
          </div>
          <svg viewBox={`0 0 ${W} ${H + 34}`}>
            {[0, 1, 2, 3].map((i) => <g key={i}><line x1={(i / 4) * W} x2={(i / 4) * W} y1="16" y2={H + 12} stroke="rgba(255,255,255,0.1)" /><text x={(i / 4) * W + W / 8} y={H + 30} textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.6)">{p.story.window[0] + i}</text></g>)}
            {rain.slice(t0, t1 + 1).map((v, i) => <rect key={i} x={x(t0 + i)} width={W / (t1 - t0) - 0.6} y={H - 4 - Math.min(v, 130) * 0.3} height={Math.min(v, 130) * 0.3} fill="#9d8cff" opacity="0.55" />)}
            <path d={line(grace)} fill="none" stroke="#ff7eb6" strokeWidth="1.6" />
            <path d={line(smap)} fill="none" stroke="#5ab0ff" strokeWidth="1.8" />
            {strip.slice(t0, t1 + 1).split('').map((c, i) => <rect key={i} x={x(t0 + i)} width={W / (t1 - t0) + 0.3} y={H + 2} height="8" fill={CLASS_COLOR[c as CoverClass]} />)}
            {p.news.filter((n) => dateToT(n.date) >= t0 && dateToT(n.date) <= t1).map((n) => <g key={n.title}><line x1={x(dateToT(n.date))} x2={x(dateToT(n.date))} y1="12" y2={H} stroke="#fff" strokeDasharray="2 2" opacity="0.6" /><rect x={x(dateToT(n.date)) - 4} y="4" width="8" height="8" fill="#fff" transform={`rotate(45 ${x(dateToT(n.date))} 8)`}><title>{n.title}</title></rect></g>)}
            {p.t >= t0 && p.t <= t1 && <line x1={x(p.t)} x2={x(p.t)} y1="0" y2={H + 12} stroke="#ffd166" strokeWidth="2" />}
          </svg>
          <p className="muted">White diamonds are headlines. The strip under the chart is what HLS saw in the field.</p>
        </div>
        <ol className="st-list">
          {p.story.chapters.map((c, i) => (
            <li key={c.date} className={i === p.idx ? 'on' : ''}><button onClick={() => p.setIdx(i)}><small>{fmtDate(c.date)}</small>{c.title}</button></li>
          ))}
        </ol>
        <div className="st-nav">
          <button className="btn ghost" disabled={p.idx === 0} onClick={() => p.setIdx(p.idx - 1)}><Icon name="left" size={16} />Back</button>
          <button className="btn" disabled={p.idx === p.story.chapters.length - 1} onClick={() => p.setIdx(p.idx + 1)} data-testid="story-next">Next<Icon name="right" size={16} /></button>
        </div>
        <p className="footnote">A signal arriving before a headline is an observation on one or two events, not a forecast.</p>
      </div>
    </section>
  );
}
