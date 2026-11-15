// Compact field timeline: scrub the date, play a season, jump to events. Drives map + Field now.
// The play clock lives in App (one interval); this bar only scrubs and shows the sim banner.
import { useRef } from 'react';
import type { Calendar, CoverClass, FieldEvent } from '../../types';
import { CLASS_COLOR, MONTHS, T_MAX, TODAY_T, dateToT, dekadOf, lastDataT, tLabel, tOf, yearOf } from '../../lib';
import Icon from '../Icons';
import { t } from '../../i18n';

const LABEL: Record<CoverClass, string> = { b: t('ui.tl.bare'), p: t('ui.tl.thin'), c: t('ui.tl.crop'), w: t('ui.tl.water'), u: t('ui.tl.noview') };

export type SimMode = {
  year: number;
  label: string;
  cover: string; // 12 monthly cover letters from the rotation
  needAf: number;
  limitAf: number;
  name: string;
} | null;

export function FieldTimeline(p: {
  t: number;
  setT: (t: number) => void;
  playing: boolean;
  setPlaying: (b: boolean) => void;
  cal: Calendar | null;
  events: FieldEvent[];
  sim: SimMode;
}) {
  const track = useRef<HTMLDivElement>(null);
  const y = yearOf(p.t), d = dekadOf(p.t);
  const last = p.cal ? yearOf(lastDataT(p.cal)) : yearOf(TODAY_T);
  const yearRow = (p.cal?.years ?? []).find((x) => x.year === y);
  const rule = yearRow?.rule ?? 'u'.repeat(36);
  const tMin = p.sim ? tOf(p.sim.year, 0) : tOf(Math.max(2016, last - 3), 0);
  const tMax = p.sim ? tOf(p.sim.year, 35) : Math.min(T_MAX, TODAY_T);
  const span = Math.max(1, tMax - tMin);
  const pct = ((Math.min(tMax, Math.max(tMin, p.t)) - tMin) / span) * 100;

  const scrub = (clientX: number) => {
    const el = track.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    p.setT(Math.round(tMin + f * span));
    p.setPlaying(false);
  };

  const month = Math.floor(d / 3);
  const simCum = p.sim ? ((month + (d % 3) / 3 + 1) / 12) * p.sim.needAf : null;
  const over = simCum != null && simCum > p.sim!.limitAf;

  return (
    <div className={`field-tl ${p.sim ? 'sim-on' : ''}`} data-testid="field-timeline">
      {p.sim && (
        <div className="sim-banner" data-testid="sim-banner">
          <b>{t('ui.tl.sim', { name: p.sim.name })}</b>
          <span>{p.sim.label} · {tLabel(p.t)}</span>
          <span className={`sim-water ${over ? 'over' : ''}`}>
            ~{simCum!.toFixed(1)} / {p.sim.limitAf.toFixed(1)} {t('ui.u.afac')}
          </span>
          <div className="sim-cover" aria-hidden>
            {p.sim.cover.split('').map((c, i) => (
              <i key={i} className={i === month ? 'now' : ''} style={{ background: CLASS_COLOR[(c as CoverClass) || 'u'] }} title={MONTHS[i]} />
            ))}
          </div>
        </div>
      )}
      <div className="ftl-bar">
        <button type="button" className="ftl-play" onClick={() => {
          if (!p.playing && p.t >= tMax) p.setT(tMin);
          p.setPlaying(!p.playing);
        }} title={p.playing ? t('ui.tl.pause') : t('ui.tl.play')} data-testid="tl-play">
          <Icon name={p.playing ? 'pause' : 'play'} size={18} />
        </button>
        <div className="ftl-date">
          <b>{tLabel(p.t)}</b>
          <span>{LABEL[(rule[d] as CoverClass) || 'u']}{p.t === TODAY_T ? ` · ${t('ui.tl.today_dot')}` : ''}</span>
        </div>
        <div
          className="ftl-track"
          ref={track}
          onPointerDown={(e) => { (e.target as HTMLElement).setPointerCapture?.(e.pointerId); scrub(e.clientX); }}
          onPointerMove={(e) => { if (e.buttons) scrub(e.clientX); }}
          role="slider"
          aria-valuemin={tMin}
          aria-valuemax={tMax}
          aria-valuenow={p.t}
          aria-label={t('ui.tl.fielddate')}
          data-testid="tl-track"
        >
          <div className="ftl-strip">
            {rule.split('').map((c, i) => (
              <i key={i} style={{ background: c === 'u' ? undefined : CLASS_COLOR[c as CoverClass] }} className={c === 'u' ? 'empty' : ''} />
            ))}
          </div>
          {p.events.filter((ev) => {
            const tt = dateToT(ev.date);
            return tt >= tMin && tt <= tMax;
          }).map((ev) => {
            const tt = dateToT(ev.date);
            return (
              <button
                key={ev.date + ev.short}
                type="button"
                className="ftl-ev"
                style={{ left: `${((tt - tMin) / span) * 100}%` }}
                title={t('ui.tl.jump', { title: ev.title })}
                onClick={(e) => { e.stopPropagation(); p.setT(tt); p.setPlaying(false); }}
              />
            );
          })}
          <span className="ftl-thumb" style={{ left: `${pct}%` }} />
        </div>
        {p.t !== TODAY_T && !p.sim && (
          <button type="button" className="ftl-today" onClick={() => { p.setT(TODAY_T); p.setPlaying(false); }}>{t('ui.tl.today')}</button>
        )}
      </div>
      <div className="ftl-years">
        {(p.sim ? [p.sim.year] : [last - 2, last - 1, last, Math.min(2026, last + 1)].filter((yy, i, a) => a.indexOf(yy) === i && yy >= 2016)).map((yy) => (
          <button key={yy} type="button" className={y === yy ? 'on' : ''} onClick={() => { p.setT(tOf(yy, Math.min(d, yy === 2026 ? dekadOf(TODAY_T) : 35))); p.setPlaying(false); }}>
            {yy}
          </button>
        ))}
      </div>
    </div>
  );
}
