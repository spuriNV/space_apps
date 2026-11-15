// Segmented control: one choice of a few (Typical / Dry / Wet year, Low / Medium / High, Rule / Model).
// The choice is a raised white thumb on a sunken track, never a green fill. Radio-group semantics, arrow keys move.
import { useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface SegOption<T> { v: T; label: ReactNode; testid?: string; disabled?: boolean; title?: string }
export function Seg<T extends string | number | boolean>(p: { label: string; value: T; options: SegOption<T>[]; onChange: (v: T) => void; className?: string; testid?: string }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const cur = Math.max(0, p.options.findIndex((o) => o.v === p.value));
  const key = (e: KeyboardEvent, i: number) => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const n = p.options.length;
    let j = i;
    for (let k = 0; k < n; k++) { j = (j + d + n) % n; if (!p.options[j].disabled) break; }
    p.onChange(p.options[j].v);
    refs.current[j]?.focus();
  };
  return (
    <div className={`seg ${p.className ?? ''}`} role="radiogroup" aria-label={p.label} data-testid={p.testid}>
      {p.options.map((o, i) => (
        <button key={String(o.v)} ref={(el) => { refs.current[i] = el; }} type="button" role="radio" aria-checked={o.v === p.value} tabIndex={i === cur ? 0 : -1}
          className={o.v === p.value ? 'on' : ''} onClick={() => p.onChange(o.v)} onKeyDown={(e) => key(e, i)} disabled={o.disabled} data-testid={o.testid} title={o.title}>{o.label}</button>
      ))}
    </div>
  );
}
