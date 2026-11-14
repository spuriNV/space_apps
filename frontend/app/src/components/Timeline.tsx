import { useRef } from 'react';
import type { Calendar, CoverClass, FieldEvent, Location, NewsItem } from '../types';
import { CLASS_COLOR, T_MAX, YEARS, clamp, dateToT, dekadOf, fmtDate, tLabel, tOf, yearOf } from '../lib';
import Icon from './Icons';
import YearSheet from './year/YearSheet';

interface Props {
  t: number; setT: (t: number) => void; playing: boolean; setPlaying: (b: boolean) => void;
  loc: Location | null; cal: Calendar | null; news: NewsItem[]; events: FieldEvent[];
  detector: 'rule' | 'ml'; setDetector: (d: 'rule' | 'ml') => void;
  expanded: boolean; setExpanded: (b: boolean) => void;
}
const EV_ICON: Record<string, string> = { drought_fallow: 'warn', atmospheric_river: 'drop', sgma_probation: 'info' };
const EV_COLOR: Record<string, string> = { drought_fallow: '#ffb44a', atmospheric_river: '#6cb6ff', sgma_probation: '#ff7eb6' };

export default function Timeline(p: Props) {
  const track = useRef<HTMLDivElement>(null);
  const drag = (clientX: number) => {
    const r = track.current!.getBoundingClientRect();
    p.setT(Math.round(clamp((clientX - r.left) / r.width, 0, 1) * T_MAX));
  };
  const onDown = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    p.setPlaying(false);
    drag(e.clientX);
  };
  const pct = (t: number) => `${(t / T_MAX) * 100}%`;
  const strip = p.cal ? p.cal.years.map((y) => (p.detector === 'rule' ? y.rule : y.ml)).join('') : null;

  return (
    <div className={`timeline glass ${p.expanded ? 'expanded' : ''}`}>
      {p.expanded && p.loc && p.cal && <YearSheet t={p.t} setT={p.setT} loc={p.loc} cal={p.cal} news={p.news} detector={p.detector} setDetector={p.setDetector} setExpanded={p.setExpanded} />}
      <div className="tl-bar">
        <button className="tl-play" onClick={() => p.setPlaying(!p.playing)} title={p.playing ? 'Pause' : 'Play through 2016–2025'} data-testid="play">
          <Icon name={p.playing ? 'pause' : 'play'} size={22} />
        </button>
        <div className="tl-date">
          <b data-testid="tl-date">{tLabel(p.t)}</b>
          <span>10-day steps · 2016–2025</span>
        </div>
        <div className="tl-track-wrap">
          <div className="tl-events">
            {p.events.map((ev, i) => {
              const t0 = dateToT(ev.date);
              return (
                <button key={ev.date + ev.type} className={`tl-ev row${i % 2} ${i === 0 ? 'left' : ''}`} style={{ left: pct(t0), color: EV_COLOR[ev.type] }} title={`${fmtDate(ev.date)} · ${ev.title}${ev.detail ? ' · ' + ev.detail : ''}`} onClick={() => p.setT(t0)}>
                  <span className="tl-ev-label"><Icon name={EV_ICON[ev.type]} size={12} />{ev.short}</span>
                  <span className="tl-ev-stem" />
                </button>
              );
            })}
          </div>
          <div className="tl-track" ref={track} onPointerDown={onDown} onPointerMove={(e) => e.buttons === 1 && drag(e.clientX)} data-testid="tl-track">
            <div className="tl-strip">
              {strip
                ? strip.split('').map((c, i) => <i key={i} style={{ background: CLASS_COLOR[c as CoverClass] }} />)
                : YEARS.map((y) => <i key={y} className="tl-empty" />)}
            </div>
            {p.events.filter((e) => e.end_date).map((e) => (
              <div key={e.date} className="tl-range" style={{ left: pct(dateToT(e.date)), width: `${((dateToT(e.end_date!) - dateToT(e.date)) / T_MAX) * 100}%`, background: EV_COLOR[e.type] }} />
            ))}
            <div className="tl-thumb" style={{ left: pct(p.t) }}><span /></div>
          </div>
          <div className="tl-years">
            {YEARS.map((y) => <button key={y} className={yearOf(p.t) === y ? 'on' : ''} onClick={() => p.setT(tOf(y, dekadOf(p.t)))}>{y}</button>)}
          </div>
        </div>
        <button className={`tl-expand ${p.expanded ? 'on' : ''}`} disabled={!p.loc} onClick={() => p.setExpanded(!p.expanded)} title={p.loc ? 'Bare / covered / water calendar, 2016–2025' : 'Pick a field first'} data-testid="year-toggle">
          <span>Your field’s year</span>
          <Icon name={p.expanded ? 'down' : 'up'} size={18} />
        </button>
      </div>
    </div>
  );
}

