import type { CoverClass, Location, Calendar, NewsItem } from '../../types';
import { CLASS_COLOR, CLASS_LABEL, MONTHS, RISK_COLOR, RISK_LABEL, dateToT, dekadOf, fmtDate, tLabel, tOf, yearOf } from '../../lib';
import Icon from '../Icons';

// "Your field's year": isolated so the redesign in design/explorations/ can replace this folder.
export interface YearSheetProps { t: number; setT: (t: number) => void; loc: Location; cal: Calendar; news: NewsItem[]; detector: 'rule' | 'ml'; setDetector: (d: 'rule' | 'ml') => void; setExpanded: (b: boolean) => void }
export default function YearSheet(p: YearSheetProps) {
  const cy = yearOf(p.t), cd = dekadOf(p.t);
  const near = [...p.news].sort((a, b) => Math.abs(dateToT(a.date) - p.t) - Math.abs(dateToT(b.date) - p.t)).slice(0, 2);
  return (
    <div className="ys" data-testid="year-sheet">
      <div className="ys-head">
        <div className="ys-title">
          <h2>Your field’s year</h2>
          <span>{p.loc.short_name} · what the 30 m satellites saw, every 10 days</span>
        </div>
        <div className="seg" role="tablist" aria-label="Detector">
          <button className={p.detector === 'rule' ? 'on' : ''} onClick={() => p.setDetector('rule')} data-testid="det-rule">Rule <i>greenness thresholds</i></button>
          <button className={p.detector === 'ml' ? 'on' : ''} onClick={() => p.setDetector('ml')} data-testid="det-ml">ML <i>random forest</i></button>
        </div>
        <div className="ys-legend">
          {(['b', 'p', 'c', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{CLASS_LABEL[c]}</span>)}
          <span><i className="hatch-u" />Unknown (cloud)</span>
          <span><i className="hatch-d" />Detectors disagree</span>
        </div>
        <button className="icon-btn" onClick={() => p.setExpanded(false)} title="Collapse"><Icon name="down" /></button>
      </div>
      <div className="ys-body">
        <div className="ys-grid">
          <div className="ys-row ys-months">
            <span className="ys-year" />
            <span className="ys-cdl">Crop on record (CDL)</span>
            <div className="ys-cells">{MONTHS.map((m) => <span key={m}>{m}</span>)}</div>
          </div>
          {p.cal.years.map((y) => {
            const s = p.detector === 'rule' ? y.rule : y.ml;
            const yearNews = p.news.filter((n) => n.date.startsWith(String(y.year)));
            return (
              <div key={y.year} className={`ys-row ${y.year === cy ? 'cur' : ''}`}>
                <span className="ys-year">{y.year}</span>
                <span className="ys-cdl" title="USDA Cropland Data Layer class for the year">{y.cdl}</span>
                <div className="ys-cells">
                  <div className="ys-ticks">
                    {y.risks.map((r, i) => <i key={i} title={`${RISK_LABEL[r.type]}: ${r.label}`} style={{ left: `${((r.dekad + 0.5) / 36) * 100}%`, background: RISK_COLOR[r.type] }} />)}
                    {yearNews.map((n) => (
                      <button key={n.date + n.title} className="ys-news" title={`${fmtDate(n.date)} · ${n.source}: ${n.title}`} style={{ left: `${((dekadOf(dateToT(n.date)) + 0.5) / 36) * 100}%` }} onClick={() => p.setT(dateToT(n.date))} />
                    ))}
                  </div>
                  <div className="ys-strip">
                    {s.split('').map((c, d) => {
                      const dis = y.rule[d] !== y.ml[d];
                      return (
                        <button key={d} className={`${c === 'u' ? 'unk' : ''} ${dis ? 'dis' : ''} ${y.year === cy && d === cd ? 'now' : ''}`} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }}
                          title={`${tLabel(tOf(y.year, d))}: ${CLASS_LABEL[c as CoverClass]}${dis ? ` (rule: ${CLASS_LABEL[y.rule[d] as CoverClass]}, ML: ${CLASS_LABEL[y.ml[d] as CoverClass]})` : ''}`}
                          onClick={() => p.setT(tOf(y.year, d))} />
                      );
                    })}
                    {y.greenup_dekad != null && <em className="mk up" style={{ left: `${(y.greenup_dekad / 36) * 100}%` }} title="Green-up" />}
                    {y.senescence_dekad != null && <em className="mk dn" style={{ left: `${(y.senescence_dekad / 36) * 100}%` }} title="Harvest / senescence" />}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <aside className="ys-rail">
          <div className="ys-agree">
            <b>{p.cal.detector_agreement_pct.value}%</b>
            <span>of clear 10-day periods, the rule and the ML detector agree. 2022 (fallow) is the held-out test year.</span>
          </div>
          <div className="ys-key">
            <h4>Risk ticks <small>above each row</small></h4>
            <div className="ys-risks">
              {(Object.keys(RISK_COLOR) as (keyof typeof RISK_COLOR)[]).map((k) => <span key={k}><i style={{ background: RISK_COLOR[k] }} />{RISK_LABEL[k]}</span>)}
              <span><i className="news-dot" />News</span>
              <span><em className="mk up inline" />Green-up</span>
              <span><em className="mk dn inline" />Harvest</span>
            </div>
            <p className="scale-line"><span className="badge-scale">30 m</span> Calendar: HLS, sees your field</p>
            <p className="scale-line"><span className="badge-scale coarse">9–50 km</span> Risk ticks: IMERG, SMAP, POWER, see your district</p>
          </div>
          <div className="ys-newslist">
            <h4>News near {tLabel(p.t)}</h4>
            {near.map((n) => (
              <a key={n.title} className="news-item" href={n.url ?? undefined} target="_blank" rel="noreferrer" onClick={(e) => { if (!n.url) e.preventDefault(); p.setT(dateToT(n.date)); }}>
                <span>{fmtDate(n.date)} · {n.source}</span>
                <b>{n.title}</b>
              </a>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
