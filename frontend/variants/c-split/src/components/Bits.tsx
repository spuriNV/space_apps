import type { CoverState, Range, RotationStrategy, SourcedNumber } from '../types';
import { getSource, mmToAfAc } from '../api';

export const COVER_LABEL: Record<CoverState, string> = { b: 'Bare', p: 'Partial', c: 'Covered', w: 'Water', u: 'Unknown' };
export const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
export const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const fmt = (n: number, d = 0) => n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtRange = (lo: number, hi: number, d = 0) => (fmt(lo, d) === fmt(hi, d) ? fmt(lo, d) : `${fmt(lo, d)}–${fmt(hi, d)}`);
export const rng = (s: SourcedNumber): Range => ({ value: s.value, low: s.low ?? s.value, high: s.high ?? s.value });

export function Icon({ name, size = 16 }: { name: string; size?: number }) {
  const p: Record<string, JSX.Element> = {
    search: <><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5" /></>,
    back: <path d="M14.5 5.5L8 12l6.5 6.5" />,
    drop: <path d="M12 3.5s6 6.3 6 10.5a6 6 0 01-12 0c0-4.2 6-10.5 6-10.5z" />,
    cow: <><path d="M5 9c0-2 2-3.5 7-3.5S19 7 19 9v5a4 4 0 01-4 4H9a4 4 0 01-4-4V9z" /><path d="M5 9L2.5 7M19 9l2.5-2M9.5 13.5h5" /></>,
    leaf: <><path d="M5 19c0-8 5-13 14-14 0 9-5 14-14 14z" /><path d="M5 19l8-8" /></>,
    rain: <><path d="M7 15a4 4 0 01.5-8 5 5 0 019.6 1.2A3.5 3.5 0 0116.5 15H7z" /><path d="M9 18l-1 2.5M13 18l-1 2.5M17 18l-1 2.5" /></>,
    soil: <><path d="M3 9h18M3 14h18M3 19h18" /><path d="M12 9V4m0 0l-2.5 2.5M12 4l2.5 2.5" /></>,
    market: <><path d="M4 9l1.5-5h13L20 9" /><path d="M4 9v10h16V9M4 9h16M9 19v-5h6v5" /></>,
    print: <><path d="M7 8V4h10v4M7 17H4.5v-7h15v7H17" /><path d="M7 14h10v6H7z" /></>,
    close: <path d="M6 6l12 12M18 6L6 18" />,
    check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
    cube: <><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M4 7.5l8 4.5 8-4.5M12 12v9" /></>,
    layers: <><path d="M12 4l9 5-9 5-9-5 9-5z" /><path d="M3 13.5l9 5 9-5" /></>,
    doc: <><path d="M7 3.5h7l4 4V20.5H7z" /><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6" /></>,
    info: <><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5.5M12 7.8v.4" /></>,
    pin: <><path d="M12 21s6.5-6.2 6.5-11a6.5 6.5 0 00-13 0c0 4.8 6.5 11 6.5 11z" /><circle cx="12" cy="10" r="2.3" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    minus: <path d="M5 12h14" />,
    arrow: <path d="M5 12h14m-5.5-5.5L19 12l-5.5 5.5" />,
    cal: <><rect x="4" y="5.5" width="16" height="14.5" rx="2" /><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {p[name]}
    </svg>
  );
}

/** 12-month strip: what is on the field each month */
export function MonthStrip({ s, labels = true, tall = false }: { s: RotationStrategy; labels?: boolean; tall?: boolean }) {
  return (
    <div className={`mstrip${tall ? ' tall' : ''}`} role="img" aria-label={`Year calendar for ${s.name}`}>
      {s.month_strip.map((m, i) => (
        <div key={i} className="mcol" title={`${MONTH_NAMES[i]}: ${m.label} (${COVER_LABEL[m.state].toLowerCase()})`}>
          <div className={`mcell cov-${m.state}`} />
          {labels && <span>{MONTHS[i]}</span>}
        </div>
      ))}
    </div>
  );
}

export function CoverLegend({ unknown = false }: { unknown?: boolean }) {
  const keys: CoverState[] = unknown ? ['b', 'p', 'c', 'w', 'u'] : ['b', 'p', 'c', 'w'];
  return (
    <div className="legend">
      {keys.map((k) => (
        <span key={k}><i className={`sw cov-${k}`} />{COVER_LABEL[k]}</span>
      ))}
    </div>
  );
}

/** Score 0–100 drawn as a range with whiskers and a centre mark */
export function ScoreRange({ r, tone = 'blue', baseline }: { r: Range; tone?: string; baseline?: number }) {
  return (
    <div className="srange" title={`${r.value} (range ${r.low}–${r.high})`}><div className="srange-in">
      <div className="srange-track" />
      <div className={`srange-fill tone-${tone}`} style={{ width: `${r.value}%` }} />
      {baseline != null && <div className="srange-base" style={{ left: `${baseline}%` }} title={`Today's rotation: ${baseline}`} />}
      <div className="srange-whisk" style={{ left: `${r.low}%`, width: `${r.high - r.low}%` }} />
    </div></div>
  );
}

export function ScoreChip({ r, big = false }: { r: Range; big?: boolean }) {
  return (
    <div className={`schip${big ? ' big' : ''}`} title="Overall fit to your priorities, 0–100. Shown as a range because the inputs are uncertain.">
      <b>{r.value}</b>
      <span>{r.low}–{r.high}</span>
    </div>
  );
}

export type AllocStatus = 'ok' | 'maybe' | 'over';
export function allocStatus(need: Range, allocMm: number): AllocStatus {
  return need.high <= allocMm ? 'ok' : need.low > allocMm ? 'over' : 'maybe';
}
export const ALLOC_TEXT: Record<AllocStatus, string> = { ok: 'Within allocation', maybe: 'May exceed allocation', over: 'Over allocation' };
export const ALLOC_SHORT: Record<AllocStatus, string> = { ok: 'Within', maybe: 'May exceed', over: 'Over' };

/** Irrigation need (range) against the allocation line */
export function WaterBar({ need, allocMm, max = 1600, compact = false }: { need: Range; allocMm: number; max?: number; compact?: boolean }) {
  const st = allocStatus(need, allocMm);
  const pct = (v: number) => `${Math.min(100, (v / max) * 100)}%`;
  return (
    <div className={`wbar${compact ? ' compact' : ''}`}>
      <div className="wbar-track">
        <div className={`wbar-range st-${st}`} style={{ left: pct(need.low), width: `${((need.high - need.low) / max) * 100}%` }} />
        <div className={`wbar-mid st-${st}`} style={{ left: pct(need.value) }} />
        <div className="wbar-alloc" style={{ left: pct(allocMm) }}><span>allocation</span></div>
      </div>
    </div>
  );
}

export function needText(need: Range) {
  return { af: `${fmtRange(mmToAfAc(need.low), mmToAfAc(need.high), 1)} acre-ft/acre`, mm: `${fmtRange(need.low, need.high)} mm` };
}

export function SourceChip({ id, n }: { id: string; n?: number }) {
  const s = getSource(id);
  if (!s) return null;
  const short = s.short ?? s.title;
  const body = (<>{n != null && <b>{n}</b>}{short}{!s.verified && <em>unverified</em>}</>);
  return s.url ? <a className={`srcchip${s.verified ? '' : ' unv'}`} href={s.url} target="_blank" rel="noreferrer" title={s.title}>{body}</a> : <span className="srcchip unv" title={s.title}>{body}</span>;
}

export function TieBadge({ s }: { s: { tie: boolean; best: boolean; is_baseline: boolean } }) {
  return (
    <>
      {s.best && !s.tie && <span className="badge best">Best fit for your priorities</span>}
      {s.best && s.tie && <span className="badge best">Top score</span>}
      {s.tie && <span className="badge tie" title="This score range overlaps the top option by more than half: the data cannot tell them apart.">Tie within uncertainty</span>}
      {s.is_baseline && <span className="badge base">Today's rotation</span>}
    </>
  );
}
