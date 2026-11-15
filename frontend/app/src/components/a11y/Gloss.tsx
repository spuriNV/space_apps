// Tap-to-explain farming terms. In Simple mode the plain-language text on the answer cards marks known terms with a dotted
// underline; each is a real button (Tab, Enter or Space) that opens a short explanation underneath, from the same glossary
// as "What's this?" (GET /api/glossary). Esc closes it and puts focus back on the term.
import { Fragment, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { glossEntry } from '../ui/What';
import { ax } from './ax';
import { usePrefs } from './prefs';

const LOCAL: Record<string, { term: string; text: string }> = {
  acreft: { term: 'Acre-foot', text: 'The water it takes to cover one acre a foot deep. 1 acre-foot per acre is the same as 12 inches of water over the field.' },
  fallow: { term: 'Fallow', text: 'A field left unplanted for a season to rest or to save water. The ground is bare.' },
  rainfed: { term: 'Rain-fed', text: 'A crop that gets all its water from rain and the soil, with no irrigation.' },
  groundwater: { term: 'Groundwater', text: 'Water stored underground, in the soil and rock below the roots. Wells pump it.' },
  rotation: { term: 'Rotation', text: 'The order of crops a field grows from year to year, such as rice then fallow.' },
};
const TERMS: [RegExp, string][] = [
  [/evapotranspiration|crop water use|\bET\b/i, 'et'], [/greenness|\bNDVI\b/i, 'greenness'], [/soil moisture/i, 'soilAnomaly'], [/\bfrost\b/i, 'frost'],
  [/water balance|irrigation need/i, 'waterBalance'], [/bare days/i, 'bare'], [/acre-?(?:ft|feet|foot)/i, 'acreft'], [/\bfallow(?:ed)?\b/i, 'fallow'],
  [/rain-fed/i, 'rainfed'], [/groundwater/i, 'groundwater'], [/\brotations?\b/i, 'rotation'], [/\bhot days\b/i, 'heat'],
];
const ALL = new RegExp(TERMS.map(([r]) => `(${r.source})`).join('|'), 'gi');
const entry = (k: string) => LOCAL[k] ?? glossEntry(k);
const BUS = 'croplytics:gloss-open';

function Term({ k, children }: { k: string; children: string }) {
  const [open, setOpen] = useState(false);
  const id = useId(), btn = useRef<HTMLButtonElement>(null);
  const e = entry(k);
  useEffect(() => {
    const other = (ev: Event) => { if ((ev as CustomEvent<string>).detail !== id) setOpen(false); };
    window.addEventListener(BUS, other);
    return () => window.removeEventListener(BUS, other);
  }, [id]);
  useEffect(() => {
    if (!open) return;
    const off = (ev: MouseEvent) => { if (!(ev.target as Element).closest?.(`[data-gloss="${CSS.escape(id)}"]`)) setOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [open, id]);
  if (!e) return <>{children}</>;
  const toggle = () => { setOpen(!open); if (!open) window.dispatchEvent(new CustomEvent(BUS, { detail: id })); };
  return (
    <span className="gloss-wrap" data-gloss={id} onKeyDown={(ev) => { if (ev.key === 'Escape' && open) { ev.stopPropagation(); setOpen(false); btn.current?.focus(); } }}>
      <button ref={btn} type="button" className="gloss" aria-expanded={open} aria-controls={open ? id : undefined} aria-label={`${children}. ${ax('glossFor', { term: e.term })}`} onClick={toggle}>{children}</button>
      {open && <span id={id} className="gloss-pop" role="note"><b>{e.term}.</b> {e.text}<button type="button" className="link-btn gloss-x" onClick={() => { setOpen(false); btn.current?.focus(); }}>{ax('glossClose')}</button></span>}
    </span>
  );
}

/** The text with known farming terms made tappable, in Simple mode only. Anything that is not a string passes through. */
export function Gloss({ children }: { children: ReactNode }) {
  const on = usePrefs().simple;
  if (!on || typeof children !== 'string') return <>{children}</>;
  const out: ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null;
  ALL.lastIndex = 0;
  while ((m = ALL.exec(children))) {
    const key = TERMS.find(([r]) => new RegExp(`^(?:${r.source})$`, 'i').test(m![0]))?.[1];
    if (key && entry(key)) { out.push(children.slice(last, m.index), <Term key={m.index} k={key}>{m[0]}</Term>); last = m.index + m[0].length; }
    if (m[0].length === 0) ALL.lastIndex++;
  }
  out.push(children.slice(last));
  return <>{out.map((x, i) => <Fragment key={i}>{x}</Fragment>)}</>;
}
