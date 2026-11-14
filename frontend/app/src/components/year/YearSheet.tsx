import type { CoverClass, Location, Calendar, CalendarYear } from '../../types';
import type { Daily } from '../../season';
import { CLASS_COLOR, MONTHS, RECENT_FROM, dateToT, dekadOf, lastDataT, tLabel, tOf, yearOf } from '../../lib';
import Icon from '../Icons';
import { cropName } from '../ui/shared';

// "Your field's year", simplified: a typical-year strip, then one strip per season (this season plus the last 3),
// one sentence on what's different, and heavy-rain days marked on each strip. Older years behind "Show earlier years".
const LABEL: Record<CoverClass, string> = { b: 'Bare', p: 'Thin cover', c: 'Crop growing', w: 'Flooded', u: 'No clear view' };
const PART = ['early', 'mid', 'late'];
const dk = (d: number) => `${PART[d % 3]} ${MONTHS[Math.floor(d / 3)]}`;
const count = (y: CalendarYear, ...cs: string[]) => y.rule.split('').filter((c) => cs.includes(c)).length * 10;

function typical(years: CalendarYear[]) {
  let s = '';
  for (let d = 0; d < 36; d++) {
    const n: Record<string, number> = {};
    years.forEach((y) => { const c = y.rule[d]; if (c !== 'u') n[c] = (n[c] ?? 0) + 1; });
    s += Object.entries(n).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'u';
  }
  return s;
}

export interface YearSheetProps { t: number; setT: (t: number) => void; loc: Location; cal: Calendar; daily: Daily | null; showEarlier: boolean; setShowEarlier: (b: boolean) => void; setExpanded: (b: boolean) => void }
export default function YearSheet(p: YearSheetProps) {
  const cy = yearOf(p.t), cd = dekadOf(p.t);
  const last = yearOf(lastDataT(p.cal));
  const past = p.cal.years.filter((y) => y.year <= last && y.rule.replace(/u/g, '').length > 6);
  const typ = typical(past);
  const typY: CalendarYear = { ...past[0], rule: typ };
  const shown = p.cal.years.filter((y) => (p.showEarlier ? true : y.year >= RECENT_FROM)).reverse();
  const ly = p.cal.years.find((y) => y.year === last)!;
  const dBare = count(ly, 'b', 'p') - count(typY, 'b', 'p'), dWater = count(ly, 'w') - count(typY, 'w');
  const diff = Math.abs(dBare) >= 20 ? `${last} had about ${Math.abs(dBare)} ${dBare > 0 ? 'more' : 'fewer'} bare or thin days than a typical year` : Math.abs(dWater) >= 20 ? `${last} was flooded about ${Math.abs(dWater)} days ${dWater > 0 ? 'longer' : 'less'} than a typical year` : `${last} looked much like a typical year`;
  const up = ly.greenup_dekad;
  const rainDays = (year: number) => (p.daily?.rows ?? []).filter((r) => r.date.startsWith(String(year)) && (r.ncei_precip_mm ?? 0) >= 25.4);
  const Strip = ({ y, cur }: { y: CalendarYear; cur: boolean }) => (
    <div className="yr-strip">
      {y.rule.split('').map((c, d) => (
        <button key={d} className={`${c === 'u' ? 'unk' : ''} ${cur && d === cd ? 'now' : ''}`} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }}
          title={`${tLabel(tOf(y.year, d))}: ${LABEL[c as CoverClass]}`} onClick={() => y.year && p.setT(tOf(y.year, d))} />
      ))}
      {y.year > 0 && rainDays(y.year).map((r) => {
        const d = dekadOf(dateToT(r.date)), c = y.rule[d];
        return <i key={r.date} className={`rain ${c === 'b' || c === 'p' ? 'hit' : ''}`} style={{ left: `${((d + 0.5) / 36) * 100}%` }} title={`${r.date}: ${(r.ncei_precip_mm! / 25.4).toFixed(1)} in of rain, field ${LABEL[c as CoverClass].toLowerCase()}`} />;
      })}
    </div>
  );
  return (
    <div className="ys" data-testid="year-sheet">
      <div className="ys-head">
        <div className="ys-title">
          <h2>This field’s year</h2>
          <p>{diff}{up != null ? `; the crop greened up in ${dk(up)}` : ''}. {last < 2026 ? `${last + 1} imagery is not processed yet.` : ''}</p>
        </div>
        <div className="ys-legend">
          {(['c', 'p', 'b', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{LABEL[c]}</span>)}
          <span><i className="hatch-u" />No clear view or not processed</span>
          <span><i className="rain-key hit" />1 inch of rain on bare ground</span>
          <span><i className="rain-key" />on a crop or water</span>
        </div>
        <button className="sq-btn" onClick={() => p.setExpanded(false)} title="Close"><Icon name="down" /></button>
      </div>
      <div className="yr-grid">
        <div className="yr-row yr-months"><span /><span /><div className="yr-m">{MONTHS.map((m) => <span key={m}>{m}</span>)}</div><span className="yr-n">Days bare or thin</span><span className="yr-n">1-inch rain days on bare ground</span></div>
        <div className="yr-row typical">
          <b>Typical year</b><span className="yr-crop">most common since {past[0]?.year}</span>
          <Strip y={{ ...typY, year: 0 }} cur={false} />
          <span className="yr-n">{count(typY, 'b', 'p')}</span><span className="yr-n" />
        </div>
        {shown.map((y) => {
          const rd = rainDays(y.year), hit = rd.filter((r) => 'bp'.includes(y.rule[dekadOf(dateToT(r.date))])).length;
          const empty = y.rule.replace(/u/g, '').length === 0;
          return (
            <div key={y.year} className={`yr-row ${y.year === cy ? 'cur' : ''}`}>
              <b>{y.year}</b><span className="yr-crop">{empty ? 'Crop map not out yet' : cropName(p.loc.crop_history[y.year])}</span>
              <Strip y={y} cur={y.year === cy} />
              <span className="yr-n">{empty ? '–' : count(y, 'b', 'p')}</span>
              <span className="yr-n">{empty || !p.daily || y.year > +p.daily.last.slice(0, 4) ? '–' : `${hit} of ${rd.length}`}</span>
            </div>
          );
        })}
      </div>
      <div className="ys-foot">
        <button className="link" onClick={() => p.setShowEarlier(!p.showEarlier)} data-testid="earlier">{p.showEarlier ? 'Show only the last 4 seasons' : 'Show earlier years (2016–2022)'}</button>
        <span className="muted">Sentinel-2 and Landsat satellites, every 10 days, whole field. Rain from NOAA stations. Click a square to move the map to that date.</span>
      </div>
    </div>
  );
}
