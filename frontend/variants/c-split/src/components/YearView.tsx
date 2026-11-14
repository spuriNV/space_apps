import { useState } from 'react';
import { getFieldYear, getNews } from '../api';
import type { CoverState, Location } from '../types';
import { COVER_LABEL, CoverLegend, MONTH_NAMES } from './Bits';

const weekOf = (date: string) => {
  const d = new Date(date + 'T00:00:00Z');
  const start = Date.UTC(d.getUTCFullYear(), 0, 1);
  return Math.min(51, Math.floor((d.getTime() - start) / (7 * 864e5)));
};
const fmtDate = (date: string) => new Date(date + 'T00:00:00Z').toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const RISK_LABEL = { rain: 'Heavy-rain day', frost: 'Frost night', heat: 'Heat day' };

export default function YearView({ loc, detector, onDetector }: { loc: Location; detector: 'rule' | 'ml'; onDetector: (d: 'rule' | 'ml') => void }) {
  const fy = getFieldYear(loc.id);
  const news = getNews(loc.id);
  const [hatch, setHatch] = useState(true);
  // one numbered marker per distinct label
  const markers = news.filter((n, i) => news.findIndex((m) => m.label === n.label) === i);
  const model = fy.models.find((m) => (detector === 'rule' ? m.method === 'rule_ndvi' : m.method !== 'rule_ndvi'))!;
  return (
    <div className="year">
      <div className="year-top">
        <div>
          <h2>Your field's year, 2016–2025</h2>
          <p>What the satellites saw each week. {loc.observed_cover.summary}.</p>
        </div>
        <div className="seg" role="group" aria-label="Detector">
          <button aria-pressed={detector === 'rule'} onClick={() => onDetector('rule')} data-detector="rule">Rule <small>NDVI thresholds</small></button>
          <button aria-pressed={detector === 'ml'} onClick={() => onDetector('ml')} data-detector="ml">ML <small>random forest</small></button>
        </div>
      </div>
      <div className="year-meta">
        <CoverLegend unknown />
        <label className="chk"><input type="checkbox" checked={hatch} onChange={(e) => setHatch(e.target.checked)} />Outline disagreement</label>
      </div>

      <div className="cal">
        <div className="cal-row cal-months">
          <span className="cal-y" />
          <div className="cal-track months">{MONTH_NAMES.map((m) => <span key={m}>{m}</span>)}</div>
          <span className="cal-crop head">Crop (CDL)</span>
        </div>
        {fy.years.map((yr) => {
          const weeks = yr.weeks[detector].split('') as CoverState[];
          const other = yr.weeks[detector === 'rule' ? 'ml' : 'rule'];
          const marks = markers.filter((n) => +n.date.slice(0, 4) === yr.year);
          return (
            <div className="cal-row" key={yr.year} data-year={yr.year}>
              <span className="cal-y">{yr.year}</span>
              <div className="cal-track">
                <div className="cal-ticks">
                  {yr.risks.map((r, i) => <i key={i} className={`tick tick-${r.type}`} style={{ left: `${((r.week + 0.5) / 52) * 100}%` }} title={`${RISK_LABEL[r.type]}, week ${r.week + 1}`} />)}
                  {marks.map((n) => (
                    <b key={n.label} className={`newspin kind-${n.kind}`} style={{ left: `${((weekOf(n.date) + 0.5) / 52) * 100}%` }} title={n.title}>{markers.indexOf(n) + 1}</b>
                  ))}
                </div>
                <div className="cal-weeks">
                  {weeks.map((w, i) => <i key={i} className={`cov-${w}${hatch && other[i] !== w ? ' dis' : ''}`} title={`${yr.year} week ${i + 1}: ${COVER_LABEL[w].toLowerCase()}${other[i] !== w ? ` (other detector: ${COVER_LABEL[other[i] as CoverState].toLowerCase()})` : ''}`} />)}
                </div>
                <div className="cal-pheno">
                  {yr.greenup_week != null && <i className="up" style={{ left: `${((yr.greenup_week + 0.5) / 52) * 100}%` }} title="Green-up" />}
                  {yr.senescence_week != null && <i className="down" style={{ left: `${((yr.senescence_week + 0.5) / 52) * 100}%` }} title="Harvest / senescence" />}
                </div>
              </div>
              <span className={`cal-crop${yr.cdl_crop.startsWith('Fallow') ? ' fallow' : ''}`}>{yr.cdl_crop}</span>
            </div>
          );
        })}
      </div>
      <div className="cal-key">
        <span><i className="tick tick-rain" />Heavy-rain day</span>
        <span><i className="tick tick-frost" />Frost night</span>
        <span><i className="tick tick-heat" />Heat day</span>
        <span><i className="ph up" />Green-up</span>
        <span><i className="ph down" />Harvest</span>
        <span className="cal-key-note" title="Risk ticks come from the regional grid (POWER, IMERG), not this field alone.">ticks: regional grid</span>
      </div>

      <div className="year-cols">
        <div className="newslist">
          <h3>In the news, next to the satellite signal</h3>
          {markers.map((n, i) => (
            <div className="newsitem" key={n.label}>
              <b className={`newspin kind-${n.kind}`}>{i + 1}</b>
              <div>
                <div className="news-t">{n.url ? <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> : n.title}</div>
                <div className="news-s">{fmtDate(n.date)} · {n.source}{!n.verified && <em> · unverified</em>}</div>
                {n.signal && <div className="news-sig"><b>NASA signal</b>{n.signal.text}<span>· lead time: computing</span></div>}
              </div>
            </div>
          ))}
        </div>
        <div className="modelcard">
          <h3>Detector check</h3>
          <div className="agree"><b>{fy.detector_agreement_pct}%</b><span>of weeks, rule and ML agree</span></div>
          <dl>
            <div><dt>Showing</dt><dd>{detector === 'rule' ? 'Rule' : 'ML'}</dd></div>
            <div><dt>Accuracy</dt><dd>{Math.round(model.metrics.accuracy * 100)}%</dd></div>
            <div><dt>Bare F1</dt><dd>{model.metrics.f1_bare.toFixed(2)}</dd></div>
            <div><dt>Timing error</dt><dd>±{model.metrics.transition_mae_days} days</dd></div>
          </dl>
          <p>{model.notes}</p>
        </div>
      </div>
    </div>
  );
}
