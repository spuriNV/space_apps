import { ReactNode, useState } from 'react';
import { CLS, Cls, SIMPLE_LABEL, Verdict } from './data';

export function Legend({ classes, simpleView }: { classes: Cls[]; simpleView?: boolean }) {
  return (
    <div className="legend">
      {classes.map((c) => (
        <span key={c} title={CLS[c].hint}>
          <i className={c === 'unknown' ? 'hatch' : ''} style={{ background: c === 'unknown' ? undefined : CLS[c].color }} />
          {simpleView ? SIMPLE_LABEL[c] : CLS[c].label}
        </span>
      ))}
    </div>
  );
}

/** Rule detector (live) vs ML detector (coming). No invented agreement numbers. */
export function Detector({ compact }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`detector ${compact ? 'compact' : ''}`}>
      <div className="det-row">
        <span className="det-label">Who decided bare vs covered</span>
        <div className="seg">
          <button className="on">Greenness rule</button>
          <button disabled title="Not built yet">Machine learning <em className="soon">coming</em></button>
        </div>
        <button className="link" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'How?'}</button>
      </div>
      {(open || !compact) && (
        <p className="det-text">
          Each clear Sentinel-2 or Landsat pass over your field is scored for greenness (NDVI): under 0.20 is bare, over 0.35 is crop.
          A second, machine-learning detector trained on USDA crop maps will check this and mark days where the two disagree. It isn’t built yet, so no agreement number is shown.
        </p>
      )}
    </div>
  );
}

const V_TEXT: Record<Verdict, string> = { better: 'Better', worse: 'Worse', unclear: 'Can’t tell', same: 'Same', none: 'Not scored yet' };
export function VerdictChip({ v, children }: { v: Verdict; children?: ReactNode }) {
  return <span className={`vchip v-${v}`}>{v === 'better' ? '▲ ' : v === 'worse' ? '▼ ' : ''}{children ?? V_TEXT[v]}</span>;
}
export const verdictText = (v: Verdict) => V_TEXT[v];

/** Ranges on one axis. Each item: label, lo, hi, best estimate. */
export function Ranges({ items, min, max, unit, ticks = 5, height = 22, overlap }: {
  items: { label: string; lo: number; hi: number; v: number; color: string }[];
  min: number; max: number; unit?: string; ticks?: number; height?: number; overlap?: [number, number] | null;
}) {
  const x = (n: number) => `${((n - min) / (max - min)) * 100}%`;
  return (
    <div className="ranges">
      {items.map((it) => (
        <div key={it.label} className="rg-row" style={{ height }}>
          <span className="rg-label">{it.label}</span>
          <div className="rg-track">
            {overlap && <div className="rg-overlap" style={{ left: x(overlap[0]), width: `calc(${x(overlap[1])} - ${x(overlap[0])})` }} />}
            <div className="rg-bar" style={{ left: x(it.lo), width: `max(4px, calc(${x(it.hi)} - ${x(it.lo)}))`, background: it.color }} />
            <div className="rg-dot" style={{ left: x(it.v), borderColor: it.color }} />
          </div>
        </div>
      ))}
      <div className="rg-row rg-axis">
        <span className="rg-label" />
        <div className="rg-track">
          {Array.from({ length: ticks }, (_, i) => min + ((max - min) * i) / (ticks - 1)).map((t) => (
            <span key={t} style={{ left: x(t) }}>{Math.round(t).toLocaleString('en-US')}{unit && t === max ? ` ${unit}` : ''}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AssumedNote() {
  return (
    <span className="badge-assumed" title="Weather and water need come from NASA POWER (real). Crop ratings, flood dates, market rule and yields are team assumptions; income and insurance history are not processed yet.">
      Engine output · real weather, many inputs assumed
    </span>
  );
}
export function RealNote({ children }: { children: ReactNode }) {
  return <span className="badge-real">{children}</span>;
}
