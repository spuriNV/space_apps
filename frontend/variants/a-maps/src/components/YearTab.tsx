import { useState } from 'react';
import { getFieldYear, getModels, getNews } from '../api';
import type { LocationId, NewsItem } from '../types';
import { COVER_COLORS, COVER_LABELS, MONTH_LETTERS, dateToWeek, fmtDate } from '../util';
import Icon from './Icon';

const CELL = 12, GAP = 1, STEP = CELL + GAP;
const RISK = [
  { key: 'extreme_rain', label: 'Heavy rain', color: '#1a73e8' },
  { key: 'frost', label: 'Frost', color: '#9334e6' },
  { key: 'heat', label: 'Heat', color: '#d93025' },
] as const;

export default function YearTab({ id, onReplayOnMap }: { id: LocationId; onReplayOnMap: (year: number) => void }) {
  const data = getFieldYear(id);
  const news = getNews(id);
  const models = getModels(id);
  const [detector, setDetector] = useState<'rule' | 'ml'>('rule');
  const [showDiff, setShowDiff] = useState(true);
  const [open, setOpen] = useState<NewsItem | null>(null);
  const ml = models.find((m) => m.method !== 'rule_ndvi')!;
  const rule = models.find((m) => m.method === 'rule_ndvi')!;
  const newsByYear = (y: number) => news.filter((n) => n.date.startsWith(String(y)));
  const latest = data.years[data.years.length - 1];

  return (
    <div className="tab-body year-tab">
      <div className="year-top">
        <div>
          <div className="h2">Your field's year</div>
          <div className="muted">One row per year, one box per week. Colour is what the satellite saw on the ground.</div>
        </div>
        <div className="year-controls">
          <div className="seg" role="group" aria-label="Detector">
            <button className={detector === 'rule' ? 'on' : ''} onClick={() => setDetector('rule')}>Simple rule</button>
            <button className={detector === 'ml' ? 'on' : ''} onClick={() => setDetector('ml')}>Machine learning</button>
          </div>
          <label className="check"><input type="checkbox" checked={showDiff} onChange={(e) => setShowDiff(e.target.checked)} />Mark where they disagree</label>
        </div>
      </div>

      <div className="legend-row">
        {(['b', 'p', 'c', 'w', 'u'] as const).map((k) => <span key={k}><i className={k === 'u' ? 'sw sw-unknown' : 'sw'} style={{ background: k === 'u' ? undefined : COVER_COLORS[k] }} />{COVER_LABELS[k]}</span>)}
        <span className="legend-gap" />
        {RISK.map((r) => <span key={r.key}><i className="tick" style={{ background: r.color }} />{r.label}</span>)}
        <span><i className="news-dot" />News</span>
      </div>

      <div className="cal">
        <div className="cal-axis" style={{ width: 52 * STEP }}>
          {MONTH_LETTERS.map((m, i) => <span key={i} style={{ left: (i * 52 * STEP) / 12 }}>{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i]}</span>)}
        </div>
        {data.years.map((y) => {
          const cls = y[detector];
          return (
            <div className="cal-row" key={y.year}>
              <span className="cal-year">{y.year}</span>
              <div className="cal-weeks" style={{ width: 52 * STEP }}>
                {cls.split('').map((c, w) => (
                  <span key={w} className={`wk${c === 'u' ? ' wk-unknown' : ''}${showDiff && y.rule[w] !== y.ml[w] ? ' wk-diff' : ''}`} style={{ left: w * STEP, background: c === 'u' ? undefined : COVER_COLORS[c] }} title={`${y.year} week ${w + 1}: ${COVER_LABELS[c]}`} />
                ))}
                {RISK.map((r, k) => y.risk_weeks[r.key].map((w) => <span key={r.key + w} className="risk-tick" style={{ left: w * STEP + 1, top: 21 + k * 4, background: r.color }} />))}
                {newsByYear(y.year).map((n) => (
                  <button key={n.date + n.title} className={`news-pin${open === n ? ' on' : ''}`} style={{ left: dateToWeek(n.date) * STEP + CELL / 2 }} onClick={() => setOpen(open === n ? null : n)} aria-label={`News: ${n.title}`}>
                    <Icon name="article" size={12} color="#fff" />
                  </button>
                ))}
              </div>
              <span className="cal-cdl">{y.cdl_class ?? <i>CDL not out yet</i>}</span>
              <span className="cal-bare">{y.bare_days} bare days</span>
            </div>
          );
        })}
        <div className="cal-row cal-vuln">
          <span className="cal-year" />
          <div className="cal-weeks" style={{ width: 52 * STEP, height: 12 }}>
            {latest.stress_weeks.map((s) => <span key={s.week} className={`vuln vuln-${s.flagged_by}`} style={{ left: s.week * STEP }} />)}
            <span className="vuln-line" />
          </div>
          <span className="cal-cdl muted">Crop stress weeks, {latest.year}</span>
          <span className="cal-bare"><i className="vuln vuln-both inline" />both models <i className="vuln vuln-one inline" />one</span>
        </div>
      </div>

      {open && (
        <div className="news-pop">
          <button className="icon-btn" onClick={() => setOpen(null)} aria-label="Close"><Icon name="close" size={18} /></button>
          <div className="news-date">{fmtDate(open.date)} · {open.source}</div>
          <div className="news-title">{open.url ? <a href={open.url} target="_blank" rel="noreferrer">{open.title}</a> : open.title}</div>
          {open.signal && <div className="news-meta"><span className="signal-chip">{open.signal.label}: {open.signal.value_pct}</span><span className="muted">Lead time: computing</span></div>}
        </div>
      )}

      <div className="year-cards">
        <div className="card">
          <div className="card-k">The two detectors agree</div>
          <div className="card-v">{data.detector_agreement_pct.value}%<span> of weeks</span></div>
          <div className="muted">Simple rule: {Math.round(rule.metrics.accuracy * 100)}% correct. Machine learning: {Math.round(ml.metrics.accuracy * 100)}% correct on held-out years ({ml.split.test_years.join(', ')}).</div>
        </div>
        <div className="card">
          <div className="card-k">News beside the satellite signal</div>
          {news.slice(0, 3).map((n) => (
            <button className="news-line" key={n.date + n.title} onClick={() => setOpen(n)}>
              <span className="news-dot" /><b>{fmtDate(n.date)}</b> {n.title}
            </button>
          ))}
        </div>
        <div className="card">
          <div className="card-k">How fine is the picture?</div>
          <div className="scale-line"><span className="scale-badge scale-field">field-scale</span>Cover colours: HLS, 30 m</div>
          <div className="scale-line"><span className="scale-badge scale-valley">valley-scale</span>Heavy rain: IMERG, ~10 km</div>
          <div className="scale-line"><span className="scale-badge scale-region">region-scale</span>Frost, heat: POWER, ~50 km</div>
          <button className="text-btn tight" onClick={() => onReplayOnMap(id === 'car_colusa_rice' ? 2023 : 2023)}><Icon name="play" size={16} />Replay 2023 on the map</button>
        </div>
      </div>
    </div>
  );
}
