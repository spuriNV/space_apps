import { Seg } from '../ui/Seg';
import { t } from '../../i18n';
import type { CoverClass, FieldEvent, Location, Calendar, CalendarYear } from '../../types';
import { useState } from 'react';
import { rainOf, type Daily } from '../../season';
import { bcGap, type Extras, type MLInfo } from '../../api';
import type { DataGap } from '../../types';
import { GapLine } from '../ui/shared';
import { DRIVER } from '../ui/FieldNow';
import { fmtDate } from '../../lib';
import { MoreDetail, useDetail } from '../ui/Detail';
import { ChartTable } from '../a11y/ChartTable';
import { CLASS_COLOR, MONTHS, RECENT_FROM, dateToT, dekadOf, lastDataT, tLabel, tOf, yearOf } from '../../lib';
import Icon from '../Icons';
import { cropName } from '../ui/shared';
import { bareDaysYear } from '../../bare';

// "Your field's year", simplified: a typical-year strip, then one strip per season (this season plus the last 3),
// one sentence on what's different, and heavy-rain days marked on each strip. Older years behind "Show earlier years".
const LABEL: Record<CoverClass, string> = { b: t('year.bare'), p: t('year.thin'), c: t('year.crop'), w: t('year.flooded'), u: t('year.noView') };
const PART = [t('year.early'), t('year.mid'), t('year.late')];
const dk = (d: number) => t('year.dekad', { part: PART[d % 3], m: MONTHS[Math.floor(d / 3)] });
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
  if (!ml && gap) return { short: t('year.naBC'), long: `${t('year.naBC')}. ${gap.reason}` };
  if (!ml) return { short: t('year.notReady'), long: t('year.mlNotReady') };
  const agree = ml.disagreePct != null ? ` ${t('year.disagree', { n: Math.round(ml.disagreePct) })}` : '';
  if (ml.estimate) return { short: t('year.estShort'), long: `${t('year.estLong')}${ml.agreeScl != null ? ` ${t('year.matchesScl', { n: pct(ml.agreeScl) })}` : ''}${agree}` };
  if (!ml.meetsTarget) return { short: t('year.belowShort'), long: `${t('year.belowLong', { n: pct(ml.acc2022) })}${agree}` };
  if (ml.inflated) return { short: t('year.secondShort'), long: `${t('year.secondLong', { n: pct(ml.acc2022) })}${agree}` };
  return { short: t('year.meetsShort'), long: `${t('year.meetsLong', { n: pct(ml.acc2022) })}${agree}` };
}
export default function YearSheet(p: YearSheetProps) {
  const cy = yearOf(p.t), cd = dekadOf(p.t);
  const detail = useDetail().on;
  const [bothRaw, setBoth] = useState(false);
  const both = bothRaw && detail;
  const gMl = bcGap(p.loc, 'ml_calendar');
  const verdict = mlVerdict(p.ml, gMl);
  const last = yearOf(lastDataT(p.cal));
  const past = (p.cal.years ?? []).filter((y) => y.year <= last && y.rule.replace(/u/g, '').length > 6);
  const typ = typical(past);
  const typY: CalendarYear = { ...past[0], rule: typ };
  const shown = (p.cal.years ?? []).filter((y) => (p.showEarlier ? true : y.year >= RECENT_FROM)).reverse();
  const ly = (p.cal.years ?? []).find((y) => y.year === last)!;
  const dBare = count(ly, 'b') - count(typY, 'b'), dWater = count(ly, 'w') - count(typY, 'w');
  const diff = Math.abs(dBare) >= 20 ? t(dBare > 0 ? 'year.moreBare' : 'year.fewerBare', { y: last, n: Math.abs(dBare) }) : Math.abs(dWater) >= 20 ? t(dWater > 0 ? 'year.floodLonger' : 'year.floodLess', { y: last, n: Math.abs(dWater) }) : t('year.looksTypical', { y: last });
  const up = ly.greenup_dekad;
  const rainDays = (year: number) => (p.daily?.rows ?? []).filter((r) => r.date.startsWith(String(year)) && (rainOf(r) ?? 0) >= 25.4);
  const yearSummary = t('year.summary', { n: shown.length, diff });
  const Strip = ({ y, cur, ml }: { y: CalendarYear; cur: boolean; ml?: boolean }) => (
    <div className={`yr-strip ${ml ? 'ml' : ''}`}>
      {(ml ? y.ml : y.rule).split('').map((c, d) => (
        <button key={d} data-c={c} className={`${c === 'u' ? 'unk' : ''} ${cur && d === cd ? 'now' : ''}`} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }}
          title={`${tLabel(tOf(y.year, d))}: ${LABEL[c as CoverClass]}${ml ? ` (${t('year.mlParen')})` : ''}`} onClick={() => y.year && p.setT(tOf(y.year, d))} />
      ))}
      {!ml && detail && y.year > 0 && (p.extras?.water?.scenes ?? []).filter((s) => s.date.startsWith(String(y.year)) && s.frac >= 0.5).map((s, si) => {
        const d = dekadOf(dateToT(s.date));
        return <i key={'w' + s.date + si} className="opera" style={{ left: `${(d / 36) * 100}%`, width: `${100 / 36}%` }} title={t('year.operaTip', { date: fmtDate(s.date), n: Math.round(s.frac * 100) })} />;
      })}
      {!ml && detail && y.year > 0 && (p.extras?.stress?.weeks ?? []).filter((w) => w.start.startsWith(String(y.year))).map((w, wi) => {
        const d = dekadOf(dateToT(w.start));
        return <i key={'s' + w.start + wi} className={`stress ${w.status}`} style={{ left: `${((d + 0.5) / 36) * 100}%` }} title={t('year.stressTip', { date: fmtDate(w.start), why: w.drivers.map((x) => DRIVER[x] ?? x).join(t('year.and')) || t('year.unusualWeek') }) + (w.tmaxC != null ? ` (${t('year.high', { n: Math.round(w.tmaxC * 9 / 5 + 32) })})` : '') + `. ${w.status === 'both' ? t('year.bothAgree') : t('year.oneOfTwo')}`} />;
      })}
      {!ml && y.year > 0 && rainDays(y.year).map((r) => {
        const d = dekadOf(dateToT(r.date)), c = y.rule[d];
        return <i key={r.date} className={`rain ${c === 'b' ? 'hit' : ''}`} style={{ left: `${((d + 0.5) / 36) * 100}%` }} title={t('year.rainTip', { date: r.date, n: ((rainOf(r) ?? 0) / 25.4).toFixed(1), c: LABEL[c as CoverClass].toLowerCase() })} />;
      })}
    </div>
  );
  return (
    <div className="ys" data-testid="year-sheet">
      <div className="ys-head">
        <div className="ys-title">
          <h2>{t('year.title')}</h2>
          <p>{diff}.{up != null ? ` ${t('year.greenFrom', { d: dk(up) })}` : ''}{last < 2026 ? ` ${t('year.notProcessed', { y: last + 1 })}` : ''}</p>
        </div>
        <Seg className="small ml-seg d-only" testid="ml-toggle" label={t('year.calendar')} value={both} onChange={setBoth}
          options={[{ v: false, label: t('year.satRule') }, { v: true, label: t('year.compareMl'), testid: 'ml-on', disabled: !p.ml, title: p.ml ? t('year.mlTitle') : verdict.long }]} />
        <div className="ys-legend">
          {(['c', 'p', 'b', 'w'] as CoverClass[]).map((c) => <span key={c}><i data-c={c} style={{ background: CLASS_COLOR[c] }} />{LABEL[c]}</span>)}
          <span><i className="hatch-u" />{t('year.keyNoView')}</span>
          <span><i className="rain-key hit" />{t('year.keyRainBare')}</span>
          <span><i className="rain-key" />{t('year.keyRainCrop')}</span>
          {detail && p.extras?.stress && <span><i className="stress-key" />{t('year.keyStress')}</span>}
          {detail && p.extras?.water && <span><i className="opera-key" />{t('year.keyOpera')}</span>}
        </div>
        {p.canReplay && <button className="ys-play ys-replay" onClick={p.onReplay} data-testid="replay-ten" title={t('year.replayTitle')}><Icon name={p.replaying ? 'pause' : 'play'} size={18} />{p.replaying ? t('year.stopReplay') : t('year.replayTen')}</button>}
        <button className="ys-play" onClick={() => p.setPlaying(!p.playing)} data-testid="play" title={p.playing ? t('year.pause') : t('year.replayMap')}><Icon name={p.playing ? 'pause' : 'play'} size={18} />{p.playing ? t('year.pause') : t('year.replayOnMap')}</button>
        <button className="icon-btn" onClick={() => p.setExpanded(false)} title={t('year.close')} aria-label={t('year.close')} data-testid="year-close"><Icon name="down" /></button>
      </div>
      {gMl && <p className="ml-note d-only"><GapLine gap={gMl} missing={!p.ml} /></p>}
      {both && <p className={`ml-note ${p.ml && !p.ml.meetsTarget && !p.ml.estimate ? 'warn' : ''}`} data-testid="ml-note"><b>{t('year.mlColon', { v: verdict.short.toLowerCase() })}</b> {verdict.long}</p>}
      <div className="yr-grid" role="group" aria-label={yearSummary}>
        <div className="yr-row yr-months"><span /><span /><div className="yr-m">{MONTHS.map((m) => <span key={m}>{m}</span>)}</div><span className="yr-n">{t('year.bareDays')}</span><span className="yr-n">{t('year.rainBareDays')}</span></div>
        <div className="yr-row typical">
          <b>{t('year.typical')}</b><span className="yr-crop" title={t('year.mostCommonTitle', { a: past[0]?.year, b: last })}>{t('year.mostCommon', { a: past[0]?.year, b: String(last).slice(2) })}</span>
          <Strip y={{ ...typY, year: 0 }} cur={false} />
          <span className="yr-n">{bareDaysYear(typY) ?? '–'}</span><span className="yr-n" />
        </div>
        {shown.map((y) => {
          const rd = rainDays(y.year), hit = rd.filter((r) => y.rule[dekadOf(dateToT(r.date))] === 'b').length;
          const empty = y.rule.replace(/u/g, '').length === 0;
          return (
            <div key={y.year} className={`yr-row ${y.year === cy ? 'cur' : ''} ${both ? 'two' : ''}`}>
              <b>{y.year}</b><span className="yr-crop">{p.loc.crop_history[y.year] ? cropName(p.loc.crop_history[y.year]) : t('year.cropMapNot')}{both && !empty && <small>{t('year.ruleMl')}</small>}</span>
              {both ? <div className="yr-two"><Strip y={y} cur={y.year === cy} /><Strip y={y} cur={false} ml /></div> : <Strip y={y} cur={y.year === cy} />}
              <span className="yr-n">{empty ? '–' : bareDaysYear(y) ?? '–'}</span>
              <span className="yr-n">{empty || !p.daily ? '–' : t('year.xOfY', { a: hit, b: rd.length })}</span>
            </div>
          );
        })}
      </div>
      <ChartTable caption={t('year.tblCaption')} head={[t('year.tblYear'), t('year.tblCrop'), t('year.tblBare'), t('year.rainBareDays')]}
        rows={shown.map((y) => { const rd = rainDays(y.year), empty = y.rule.replace(/u/g, '').length === 0; return [y.year, p.loc.crop_history[y.year] ? cropName(p.loc.crop_history[y.year]) : t('year.cropMapNot'), empty ? t('year.noData') : bareDaysYear(y) ?? t('year.noData'), empty || !p.daily ? t('year.noData') : t('year.xOfY', { a: rd.filter((r) => y.rule[dekadOf(dateToT(r.date))] === 'b').length, b: rd.length })]; })} />
      <div className="ys-foot">
        <span className="ys-md"><MoreDetail what={t('year.moreWhat')} /></span>
        {p.events.length > 0 && <span className="ys-events">{p.events.map((e) => <button key={e.date + e.type} className="link" onClick={() => p.setT(dateToT(e.date))} title={e.title}>{e.short}</button>)}</span>}
        <button className="link d-only" onClick={() => p.setShowEarlier(!p.showEarlier)} data-testid="earlier">{p.showEarlier ? t('year.onlyLast4') : t('year.showEarlier')}</button>
        <span className="muted">{p.calSource}{t('year.every10')}{both ? ` ${t('year.mlFoot', { m: p.ml?.model ?? t('year.randomForest') })}` : ''} {t('year.footEnd')}</span>
      </div>
    </div>
  );
}
