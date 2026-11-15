import { Seg } from '../ui/Seg';
import type { CoverClass, FieldEvent, Location, Calendar, CalendarYear } from '../../types';
import { useState } from 'react';
import { rainOf, type Daily } from '../../season';
import { bcGap, type Extras, type MLInfo } from '../../api';
import type { DataGap } from '../../types';
import { GapLine } from '../ui/shared';
import { DRIVER } from '../ui/FieldNow';
import { fmtDate } from '../../lib';
import { MoreDetail, useDetail } from '../ui/Detail';
import { CLASS_COLOR, MONTHS, RECENT_FROM, dateToT, dekadOf, lastDataT, tLabel, tOf, yearOf } from '../../lib';
import Icon from '../Icons';
import { cropName } from '../ui/shared';
import { bareDaysYear } from '../../bare';

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

export interface YearSheetProps { events: FieldEvent[]; playing: boolean; setPlaying: (b: boolean) => void; extras: Extras | null; calSource: string; t: number; setT: (t: number) => void; loc: Location; cal: Calendar; daily: Daily | null; ml: MLInfo | null; showEarlier: boolean; setShowEarlier: (b: boolean) => void; setExpanded: (b: boolean) => void; canReplay?: boolean; replaying?: boolean; onReplay?: () => void }

const pct = (x: number | null) => (x == null ? '?' : `${Math.round(x * 100)}%`);
/** What the machine-learning calendar is worth on this field, in plain words. */
export function mlVerdict(ml: MLInfo | null, gap?: DataGap | null) {
  if (!ml && gap) return { short: 'Not available in BC', long: `Not available in BC. ${gap.reason}` };
  if (!ml) return { short: 'Not ready for this field yet', long: 'The machine-learning calendar is not ready for this field yet.' };
  const agree = ml.disagreePct != null ? ` The two disagree on ${Math.round(ml.disagreePct)}% of clear satellite days.` : '';
  if (ml.estimate) return { short: 'An estimate, not a trained model', long: `A simpler two-class greenness rule run on this field only.${ml.agreeScl != null ? ` It matches Sentinel-2’s own scene labels on ${pct(ml.agreeScl)} of clear views.` : ''}${agree}` };
  if (!ml.meetsTarget) return { short: 'Below accuracy target', long: `Below our accuracy target on this field: in 2022, a year it never trained on, it was right ${pct(ml.acc2022)} of the time against a target of 85%, and it misses bare ground too often. The rule calendar stays the answer; this is for comparison only.${agree}` };
  if (ml.inflated) return { short: 'Second opinion only', long: `In 2022, a year it never trained on, it scored ${pct(ml.acc2022)}. That is too good to take at face value: the model partly learned how its training labels were made. Shown as a second opinion next to the rule, not as the answer.${agree}` };
  return { short: 'Meets accuracy target', long: `Meets our accuracy target on this field (right ${pct(ml.acc2022)} of the time in 2022, a year it never trained on). Shown next to the rule as a comparison.${agree}` };
}
export default function YearSheet(p: YearSheetProps) {
  const cy = yearOf(p.t), cd = dekadOf(p.t);
  const detail = useDetail().on;
  const [bothRaw, setBoth] = useState(false);
  const both = bothRaw && detail;
  const gMl = bcGap(p.loc, 'ml_calendar');
  const verdict = mlVerdict(p.ml, gMl);
  const last = yearOf(lastDataT(p.cal));
  const past = p.cal.years.filter((y) => y.year <= last && y.rule.replace(/u/g, '').length > 6);
  const typ = typical(past);
  const typY: CalendarYear = { ...past[0], rule: typ };
  const shown = p.cal.years.filter((y) => (p.showEarlier ? true : y.year >= RECENT_FROM)).reverse();
  const ly = p.cal.years.find((y) => y.year === last)!;
  const dBare = count(ly, 'b') - count(typY, 'b'), dWater = count(ly, 'w') - count(typY, 'w');
  const diff = Math.abs(dBare) >= 20 ? `${last} had about ${Math.abs(dBare)} ${dBare > 0 ? 'more' : 'fewer'} bare days than a typical year` : Math.abs(dWater) >= 20 ? `${last} was flooded about ${Math.abs(dWater)} days ${dWater > 0 ? 'longer' : 'less'} than a typical year` : `${last} looked much like a typical year`;
  const up = ly.greenup_dekad;
  const rainDays = (year: number) => (p.daily?.rows ?? []).filter((r) => r.date.startsWith(String(year)) && (rainOf(r) ?? 0) >= 25.4);
  const Strip = ({ y, cur, ml }: { y: CalendarYear; cur: boolean; ml?: boolean }) => (
    <div className={`yr-strip ${ml ? 'ml' : ''}`}>
      {(ml ? y.ml : y.rule).split('').map((c, d) => (
        <button key={d} className={`${c === 'u' ? 'unk' : ''} ${cur && d === cd ? 'now' : ''}`} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }}
          title={`${tLabel(tOf(y.year, d))}: ${LABEL[c as CoverClass]}${ml ? ' (machine learning)' : ''}`} onClick={() => y.year && p.setT(tOf(y.year, d))} />
      ))}
      {!ml && detail && y.year > 0 && (p.extras?.water?.scenes ?? []).filter((s) => s.date.startsWith(String(y.year)) && s.frac >= 0.5).map((s, si) => {
        const d = dekadOf(dateToT(s.date));
        return <i key={'w' + s.date + si} className="opera" style={{ left: `${(d / 36) * 100}%`, width: `${100 / 36}%` }} title={`${fmtDate(s.date)}: NASA OPERA saw ${Math.round(s.frac * 100)}% of the field under water`} />;
      })}
      {!ml && detail && y.year > 0 && (p.extras?.stress?.weeks ?? []).filter((w) => w.start.startsWith(String(y.year))).map((w, wi) => {
        const d = dekadOf(dateToT(w.start));
        return <i key={'s' + w.start + wi} className={`stress ${w.status}`} style={{ left: `${((d + 0.5) / 36) * 100}%` }} title={`Week of ${fmtDate(w.start)}: crop stress, ${w.drivers.map((x) => DRIVER[x] ?? x).join(' and ') || 'an unusual week'}${w.tmaxC != null ? ` (high ${Math.round(w.tmaxC * 9 / 5 + 32)} °F)` : ''}. ${w.status === 'both' ? 'Both methods agree.' : 'One of two methods.'}`} />;
      })}
      {!ml && y.year > 0 && rainDays(y.year).map((r) => {
        const d = dekadOf(dateToT(r.date)), c = y.rule[d];
        return <i key={r.date} className={`rain ${c === 'b' ? 'hit' : ''}`} style={{ left: `${((d + 0.5) / 36) * 100}%` }} title={`${r.date}: ${((rainOf(r) ?? 0) / 25.4).toFixed(1)} in of rain, field ${LABEL[c as CoverClass].toLowerCase()}`} />;
      })}
    </div>
  );
  return (
    <div className="ys" data-testid="year-sheet">
      <div className="ys-head">
        <div className="ys-title">
          <h2>This field’s year</h2>
          <p>{diff}.{up != null ? ` Green from ${dk(up)}.` : ''}{last < 2026 ? ` ${last + 1} not processed yet.` : ''}</p>
        </div>
        <Seg className="small ml-seg d-only" testid="ml-toggle" label="Calendar" value={both} onChange={setBoth}
          options={[{ v: false, label: 'Satellite rule' }, { v: true, label: 'Compare with machine learning', testid: 'ml-on', disabled: !p.ml, title: p.ml ? 'Show the machine-learning calendar under the rule, season by season' : verdict.long }]} />
        <div className="ys-legend">
          {(['c', 'p', 'b', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{LABEL[c]}</span>)}
          <span><i className="hatch-u" />No clear view or not processed</span>
          <span><i className="rain-key hit" />1 inch of rain on bare ground</span>
          <span><i className="rain-key" />on a crop or water</span>
          {detail && p.extras?.stress && <span><i className="stress-key" />Crop-stress week (hover for why)</span>}
          {detail && p.extras?.water && <span><i className="opera-key" />Standing water seen by NASA OPERA</span>}
        </div>
        {p.canReplay && <button className="ys-play ys-replay" onClick={p.onReplay} data-testid="replay-ten" title="Fly in and replay this field's satellite record, 2016 to 2026"><Icon name={p.replaying ? 'pause' : 'play'} size={18} />{p.replaying ? 'Stop replay' : 'Replay ten years'}</button>}
        <button className="ys-play" onClick={() => p.setPlaying(!p.playing)} data-testid="play" title={p.playing ? 'Pause' : 'Replay the seasons on the map'}><Icon name={p.playing ? 'pause' : 'play'} size={18} />{p.playing ? 'Pause' : 'Replay on the map'}</button>
        <button className="icon-btn" onClick={() => p.setExpanded(false)} title="Close" aria-label="Close" data-testid="year-close"><Icon name="down" /></button>
      </div>
      {gMl && <p className="ml-note d-only"><GapLine gap={gMl} missing={!p.ml} /></p>}
      {both && <p className={`ml-note ${p.ml && !p.ml.meetsTarget && !p.ml.estimate ? 'warn' : ''}`} data-testid="ml-note"><b>Machine learning: {verdict.short.toLowerCase()}.</b> {verdict.long}</p>}
      <div className="yr-grid">
        <div className="yr-row yr-months"><span /><span /><div className="yr-m">{MONTHS.map((m) => <span key={m}>{m}</span>)}</div><span className="yr-n">Bare days a year</span><span className="yr-n">1-inch rain days on bare ground</span></div>
        <div className="yr-row typical">
          <b>Typical year</b><span className="yr-crop" title={`Most common cover for each 10 days, ${past[0]?.year}–${last}`}>most common, {past[0]?.year}–{String(last).slice(2)}</span>
          <Strip y={{ ...typY, year: 0 }} cur={false} />
          <span className="yr-n">{bareDaysYear(typY) ?? '–'}</span><span className="yr-n" />
        </div>
        {shown.map((y) => {
          const rd = rainDays(y.year), hit = rd.filter((r) => y.rule[dekadOf(dateToT(r.date))] === 'b').length;
          const empty = y.rule.replace(/u/g, '').length === 0;
          return (
            <div key={y.year} className={`yr-row ${y.year === cy ? 'cur' : ''} ${both ? 'two' : ''}`}>
              <b>{y.year}</b><span className="yr-crop">{p.loc.crop_history[y.year] ? cropName(p.loc.crop_history[y.year]) : 'Crop map not out yet'}{both && !empty && <small>rule / machine learning</small>}</span>
              {both ? <div className="yr-two"><Strip y={y} cur={y.year === cy} /><Strip y={y} cur={false} ml /></div> : <Strip y={y} cur={y.year === cy} />}
              <span className="yr-n">{empty ? '–' : bareDaysYear(y) ?? '–'}</span>
              <span className="yr-n">{empty || !p.daily ? '–' : `${hit} of ${rd.length}`}</span>
            </div>
          );
        })}
      </div>
      <div className="ys-foot">
        <span className="ys-md"><MoreDetail what="Machine learning, earlier years" /></span>
        {p.events.length > 0 && <span className="ys-events">{p.events.map((e) => <button key={e.date + e.type} className="link" onClick={() => p.setT(dateToT(e.date))} title={e.title}>{e.short}</button>)}</span>}
        <button className="link d-only" onClick={() => p.setShowEarlier(!p.showEarlier)} data-testid="earlier">{p.showEarlier ? 'Show only the last 4 seasons' : 'Show earlier years (2016–2022)'}</button>
        <span className="muted">{p.calSource}, every 10 days, whole field.{both ? ` Machine learning: ${p.ml?.model ?? 'random forest'} on Sentinel-2, trained on neighbouring fields.` : ''} Rain from NASA GPM IMERG. Click a square to move the map to that date.</span>
      </div>
    </div>
  );
}
