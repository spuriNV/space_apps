import { useRef } from 'react';
import type { Calendar, CoverClass, FieldEvent, Location } from '../types';
import type { Daily } from '../season';
import type { Extras, MLInfo, Prov } from '../api';
import { calSource } from './ui/shared';
import { CLASS_COLOR, RECENT_FROM, TODAY_T, T_MAX, YEARS, clamp, dateToT, dekadOf, fmtDate, tLabel, tOf, yearOf } from '../lib';
import Icon from './Icons';
import YearSheet from './year/YearSheet';

interface Props {
  t: number; setT: (t: number) => void; playing: boolean; setPlaying: (b: boolean) => void;
  loc: Location | null; cal: Calendar | null; daily: Daily | null; ml: MLInfo | null; prov?: Prov; extras?: Extras | null; events: FieldEvent[];
  showEarlier: boolean; setShowEarlier: (b: boolean) => void;
  expanded: boolean; setExpanded: (b: boolean) => void;
}
const EV_ICON: Record<string, string> = { drought_fallow: 'warn', atmospheric_river: 'drop', sgma_probation: 'info' };
const EV_COLOR: Record<string, string> = { drought_fallow: '#8a5a00', atmospheric_river: '#1b5e9e', sgma_probation: '#8a2a5a' };

/** First 10-day step shown on the timeline: this season plus the last 3 by default. */
export const tStart = (showEarlier: boolean) => tOf(showEarlier ? YEARS[0] : RECENT_FROM, 0);

export default function Timeline(p: Props) {
  const track = useRef<HTMLDivElement>(null);
  const T0 = tStart(p.showEarlier), span = T_MAX - T0;
  const years = YEARS.filter((y) => y >= yearOf(T0));
  const drag = (clientX: number) => {
    const r = track.current!.getBoundingClientRect();
    p.setT(T0 + Math.round(clamp((clientX - r.left) / r.width, 0, 1) * span));
  };
  const onDown = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    p.setPlaying(false);
    drag(e.clientX);
  };
  const pct = (t: number) => `${((t - T0) / span) * 100}%`;
  const strip = p.cal ? p.cal.years.filter((y) => y.year >= yearOf(T0)).map((y) => y.rule).join('') : null;
  const evs = p.events.filter((e) => dateToT(e.date) >= T0);

  return (
    <div className={`timeline glass ${p.expanded ? 'expanded' : ''}`}>
      {p.expanded && p.loc && p.cal && <YearSheet extras={p.extras ?? null} calSource={calSource(p.prov)} t={p.t} setT={p.setT} loc={p.loc} cal={p.cal} daily={p.daily} ml={p.ml} showEarlier={p.showEarlier} setShowEarlier={p.setShowEarlier} setExpanded={p.setExpanded} />}
      <div className="tl-bar">
        <button className="tl-play" onClick={() => p.setPlaying(!p.playing)} title={p.playing ? 'Pause' : `Play through ${yearOf(T0)}–2026`} data-testid="play">
          <Icon name={p.playing ? 'pause' : 'play'} size={22} />
        </button>
        <div className="tl-date">
          <b data-testid="tl-date">{p.t === TODAY_T ? 'Today' : tLabel(p.t)}</b>
          <span>{p.t === TODAY_T ? tLabel(p.t) : <button className="link" onClick={() => p.setT(TODAY_T)}>Back to today</button>}</span>
        </div>
        <div className="tl-track-wrap">
          <div className="tl-events">
            {evs.map((ev, i) => {
              const t0 = dateToT(ev.date);
              return (
                <button key={ev.date + ev.type} className={`tl-ev row${i % 2} ${t0 - T0 < span * 0.12 ? '' : t0 - T0 > span * 0.8 ? 'left' : ''}`} style={{ left: pct(t0), color: EV_COLOR[ev.type] }} title={`${fmtDate(ev.date)} · ${ev.title}${ev.detail ? ' · ' + ev.detail : ''}`} onClick={() => p.setT(t0)}>
                  <span className="tl-ev-label"><Icon name={EV_ICON[ev.type]} size={12} />{ev.short}</span>
                  <span className="tl-ev-stem" />
                </button>
              );
            })}
          </div>
          <div className="tl-track" ref={track} onPointerDown={onDown} onPointerMove={(e) => e.buttons === 1 && drag(e.clientX)} data-testid="tl-track">
            <div className="tl-strip">
              {strip
                ? strip.split('').map((c, i) => <i key={i} className={c === 'u' ? 'unk' : ''} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }} />)
                : years.map((y) => <i key={y} className="tl-empty" />)}
            </div>
            <div className="tl-today" style={{ left: pct(TODAY_T) }} title="Today" />
            {p.t >= T0 && <div className="tl-thumb" style={{ left: pct(p.t) }}><span /></div>}
          </div>
          <div className="tl-years" style={{ gridTemplateColumns: `repeat(${years.length}, 1fr)` }}>
            {years.map((y) => <button key={y} className={yearOf(p.t) === y ? 'on' : ''} onClick={() => p.setT(y === 2026 ? TODAY_T : tOf(y, dekadOf(p.t)))}>{y}{y === 2026 ? ', this season' : ''}</button>)}
          </div>
        </div>
        <div className="tl-side">
          <button className="link" onClick={() => p.setShowEarlier(!p.showEarlier)} data-testid="tl-earlier">{p.showEarlier ? 'Last 4 seasons only' : 'Show earlier years'}</button>
          <button className={`tl-expand ${p.expanded ? 'on' : ''}`} disabled={!p.loc} onClick={() => p.setExpanded(!p.expanded)} title={p.loc ? 'Bare, green or flooded, season by season' : 'Pick a field first'} data-testid="year-toggle">
            <span>This field’s year</span>
            <Icon name={p.expanded ? 'down' : 'up'} size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
