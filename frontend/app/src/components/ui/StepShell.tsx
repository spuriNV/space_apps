// One frame for every step of the flow (2 Your field now, 3 Coming season, 4 Compare, 5 Print), so the grower learns the
// layout once: the same floating card over the map on a computer, the same draggable bottom sheet on a phone. Inside, the
// same order on every step (the GOV.UK "one question per page" pattern and FieldView/Operations Center field cards):
//   Step N of 5 + the field -> the question -> the answer in one line -> two or three key facts -> step controls ->
//   More detail (everything else, unchanged) -> footer with Back and Next.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode, type PointerEvent as RPointerEvent, type KeyboardEvent as RKeyboardEvent } from 'react';
import Icon from '../Icons';
import { MoreDetail } from './Detail';
import { ReadAloud } from '../help/ReadAloud';
import { FLOW, StepLine, type FlowId } from './shared';
import { usePrefs } from '../a11y/prefs';
import { Gloss } from '../a11y/Gloss';
import { ax, easy } from '../a11y/ax';

export type Tone = 'good' | 'warn' | 'neutral';
export interface Fact { label: string; value: ReactNode; tone?: Tone }

/** The answer to the step's question, big and plain: "No. Short by about 0.9 acre-ft per acre." */
export function Answer({ tone = 'neutral', headline, sub, loading, speak }: { tone?: Tone; headline: ReactNode; sub?: ReactNode; loading?: boolean; speak?: string }) {
  const { simple } = usePrefs();
  // Simple mode: short sentences (the first one), and farming terms can be tapped for a plain explanation
  if (simple && typeof sub === 'string') sub = easy(sub);
  if (loading) return <div className="step-answer" aria-busy="true"><span className="skel skel-val" /><span className="skel" /></div>;
  return (
    <div className={`step-answer ${tone}`} data-testid="step-answer" role="status">
      <i className="sa-dot" aria-hidden="true">{tone === 'good' ? <Icon name="check" size={18} /> : tone === 'warn' ? '!' : null}</i>
      <div><b><Gloss>{headline}</Gloss></b>{sub && <span><Gloss>{sub}</Gloss></span>}{speak && <ReadAloud text={speak} />}</div>
    </div>
  );
}

/** Two or three supporting facts, label left and value right, one hairline between them. */
export function KeyFacts({ facts }: { facts: Fact[] }) {
  return (
    <dl className="key-facts" data-testid="key-facts">
      {facts.map((f) => <div key={f.label} className={f.tone ?? ''}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}
    </dl>
  );
}

/** The grower's water limit, set where it is first used (step 2): − / + in tenths and a slider. "example" until changed. */
export function LimitControl({ value, example, onChange }: { value: number; example: boolean; onChange: (v: number) => void }) {
  const set = (v: number) => onChange(Math.round(Math.min(8, Math.max(0.5, v)) * 10) / 10);
  return (
    <div className="limit-ctl" data-testid="limit-ctl">
      <div className="lc-row">
        <label htmlFor="alloc">Water you can get each year<small>From your district or wells. 1 acre-ft per acre = 12 inches over the field.</small>{example && <small><em className="status example ex-limit">example, change to yours</em></small>}</label>
        <div className="lc-step">
          <button type="button" className="icon-btn" onClick={() => set(value - 0.1)} aria-label="Lower by 0.1"><Icon name="minus" size={18} /></button>
          <output htmlFor="alloc" aria-live="polite"><b>{value.toFixed(1)}</b><small>acre-ft/acre</small></output>
          <button type="button" className="icon-btn" onClick={() => set(value + 0.1)} aria-label="Raise by 0.1"><Icon name="plus" size={18} /></button>
        </div>
      </div>
      <input id="alloc" type="range" min={0.5} max={8} step={0.1} value={value} onChange={(e) => set(+e.target.value)} data-testid="alloc" aria-label="Water you can get each year, acre-feet per acre" />
    </div>
  );
}

/** One question with two to four answers, as pills (step 4's farm questions). */
export function Choice<T extends string>({ label, hint, value, options, onChange, disabled, testid }: { label: string; hint?: string; value: T; options: { v: T; label: string }[]; onChange: (v: T) => void; disabled?: boolean; testid?: string }) {
  return (
    <fieldset className="choice" data-testid={testid} disabled={disabled}>
      <legend>{label}{hint && <small>{hint}</small>}</legend>
      <div className="chips choice-pills">
        {options.map((o) => <button key={o.v} type="button" className="chip" aria-pressed={value === o.v} onClick={() => onChange(o.v)}><Icon name="check" size={16} className="check" />{o.label}</button>)}
      </div>
    </fieldset>
  );
}

export interface StepShellProps {
  id: FlowId;
  /** the field, small, above the question: keeps the grower oriented on every step */
  field: ReactNode;
  /** the one question this step answers */
  title: ReactNode;
  answer?: ReactNode;
  children?: ReactNode;
  /** everything else, shown only with More detail on */
  detail?: ReactNode;
  detailWhat?: string;
  next?: { label: string; sub?: string; onClick: () => void; icon?: string; testid?: string };
  onBack?: () => void;
  onClose: () => void;
  onSheet?: (visiblePx: number) => void;
  /** a key that changes when the content should start again at the top (a new field) */
  resetKey?: string;
  testid?: string;
  className?: string;
  /** extra content after the header, before the answer (notices) */
  top?: ReactNode;
  after?: ReactNode;
}

export function StepShell(p: StepShellProps) {
  const sheet = useSheet(p.onSheet);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [footStuck, setFootStuck] = useState(false);
  const onScroll = useCallback(() => { const el = scrollRef.current; if (el) setFootStuck(el.scrollTop + el.clientHeight < el.scrollHeight - 1); }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ top: 0 }); onScroll(); }, [p.resetKey, p.id, onScroll]);
  useEffect(() => { const h = setTimeout(onScroll, 400); return () => clearTimeout(h); });
  useEffect(() => { if (sheet.snap !== 'full') scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' }); }, [sheet.snap]);
  const step = FLOW.find((f) => f.id === p.id)!;
  // Simple mode: only the answer and the next button until "Show more"
  const { simple } = usePrefs();
  const [more, setMore] = useState(false);
  useEffect(() => setMore(false), [p.id, p.resetKey]);
  return (
    <aside ref={sheet.ref} id="field-panel" tabIndex={-1} className={`panel fpanel step-shell step-${p.id} sheet-${sheet.snap} ${simple ? 'simple' : ''} ${more ? 'more' : ''} ${p.className ?? ''}`} data-testid={p.testid} aria-label={`Step ${step.n} of ${FLOW.length}: ${step.label}`} {...sheet.handlers}>
      <button className="fp-grab" onClick={sheet.cycle} onKeyDown={sheet.onKey} aria-label="Resize the panel" data-testid="grab"><i /></button>
      <div className="fp-body">
        <button className="icon-btn fp-close" onClick={p.onClose} title="Close" aria-label="Close"><Icon name="close" size={20} /></button>
        <div className="panel-scroll" ref={scrollRef} onScroll={onScroll}>
          <div className="fp-content" key={p.resetKey}>
            <header className="fp-head step-head">
              <StepLine id={p.id} />
              <p className="step-field">{p.field}</p>
              <h1>{p.title}</h1>
            </header>
            {p.top}
            {p.answer}
            {simple && <button type="button" className="btn btn-outline simple-more-btn" aria-expanded={more} onClick={() => setMore(!more)} data-testid="simple-more">{more ? ax('showLess') : ax('showMore')}</button>}
            {p.children}
            {p.detail && <>
              <MoreDetail what={p.detailWhat ?? 'Sources and the full numbers'} />
              <div className="fp-more"><div className="fp-more-in">{p.detail}</div></div>
            </>}
            {p.after}
          </div>
        </div>
      </div>
      <footer className={`fp-foot step-foot ${footStuck ? 'stuck' : ''}`}>
        {p.onBack && <button className="btn btn-outline step-back" onClick={p.onBack} data-testid="step-back"><Icon name="left" size={20} />Back</button>}
        {p.next && <button className="btn btn-primary next-step" onClick={p.next.onClick} data-testid={p.next.testid}>
          {p.next.icon && <Icon name={p.next.icon} size={20} />}
          <span><b>{p.next.label}</b>{p.next.sub && <small>{p.next.sub}</small>}</span>{!p.next.icon && <Icon name="right" size={20} />}
        </button>}
      </footer>
    </aside>
  );
}

type Snap = 'peek' | 'half' | 'full';
const SNAPS: Snap[] = ['peek', 'half', 'full'];
const PHONE = '(max-width: 640px)';
/** Phone bottom sheet: snap points peek (128px), half (52% of the screen) and full. The sheet follows the finger by
 *  transform only; on release it goes to the nearest snap point, or to the next one in the direction of a fling
 *  (faster than 0.5 px/ms). Tap the handle to cycle; arrow keys on the handle step. Content scrolls only at full;
 *  below that, a drag anywhere on the sheet moves the sheet (the Google Maps behaviour). */
export function useSheet(onSheet?: (visiblePx: number) => void, opts?: { initial?: Snap; peek?: () => number }) {
  const ref = useRef<HTMLElement>(null);
  const [snap, setSnap] = useState<Snap>(opts?.initial ?? 'half');
  const peekPx = () => opts?.peek?.() ?? 128;
  const drag = useRef<{ id: number; y0: number; off0: number; last: number; t: number; v: number; on: boolean } | null>(null);
  const dragged = useRef(false);
  const phone = () => window.matchMedia(PHONE).matches;
  const offOf = (s: Snap) => {
    const h = ref.current?.offsetHeight ?? 0;
    return s === 'full' ? 0 : Math.max(0, h - (s === 'half' ? Math.round(window.innerHeight * 0.52) : peekPx()));
  };
  const curOff = () => { const el = ref.current; return el ? new DOMMatrixReadOnly(getComputedStyle(el).transform).m42 : 0; };
  const go = useCallback((s: Snap) => {
    const el = ref.current;
    if (!el || !phone()) return;
    el.style.setProperty('--sheet-off', `${offOf(s)}px`);
    setSnap(s);
    onSheet?.((el.offsetHeight ?? 0) - offOf(s));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSheet]);
  // place the sheet before the first paint (the CSS entrance then slides it up from below), and again on resize
  useLayoutEffect(() => {
    const fit = () => { if (phone()) go(snap); else ref.current?.style.removeProperty('--sheet-off'); };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap]);
  const onPointerDown = (e: RPointerEvent) => {
    if (!phone() || (e.pointerType === 'mouse' && e.button !== 0)) return;
    const handle = (e.target as Element).closest('.fp-grab, .fp-bar, .fp-head, .pk-head');
    if (snap === 'full' && !handle) return; // at full the content scrolls; the handle and header still move the sheet
    drag.current = { id: e.pointerId, y0: e.clientY, off0: curOff(), last: e.clientY, t: e.timeStamp, v: 0, on: false };
    // a mouse drag from the handle or header keeps its moves even when it leaves the sheet (touch has implicit capture)
    if (handle && e.pointerType === 'mouse') (handle as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: RPointerEvent) => {
    const d = drag.current, el = ref.current;
    if (!d || !el || e.pointerId !== d.id) return;
    const dy = e.clientY - d.y0;
    if (!d.on) {
      if (Math.abs(dy) < 6) return;
      if (snap === 'full' && dy < 0) { drag.current = null; return; } // already at the top: let the content scroll
      d.on = true; if (!el.hasPointerCapture(e.pointerId) && !(e.target as Element).hasPointerCapture?.(e.pointerId)) el.setPointerCapture(e.pointerId); el.classList.add('dragging');
    }
    const max = offOf('peek');
    let off = d.off0 + dy;
    if (off < 0) off = -Math.pow(-off, 0.7); // rubber band past the top and past peek
    else if (off > max) off = max + Math.pow(off - max, 0.7);
    el.style.setProperty('--sheet-off', `${off}px`);
    const dt = e.timeStamp - d.t;
    if (dt > 0) d.v = 0.7 * ((e.clientY - d.last) / dt) + 0.3 * d.v;
    d.last = e.clientY; d.t = e.timeStamp;
  };
  const onPointerUp = (e: RPointerEvent) => {
    const d = drag.current, el = ref.current;
    drag.current = null;
    if (!d || !d.on || !el) return;
    el.classList.remove('dragging');
    dragged.current = true; setTimeout(() => { dragged.current = false; }, 0);
    const off = curOff(), v = e.timeStamp - d.t > 90 ? 0 : d.v;
    const offs = SNAPS.map(offOf);
    let target: Snap;
    if (Math.abs(v) > 0.5) {
      // fling: the next snap point in that direction (down = a larger offset)
      const order = SNAPS.map((s, i) => ({ s, o: offs[i] })).sort((a, b) => a.o - b.o);
      const next = v > 0 ? order.find((x) => x.o > off + 1) ?? order[order.length - 1] : [...order].reverse().find((x) => x.o < off - 1) ?? order[0];
      target = next.s;
    } else target = SNAPS.reduce((a, s, i) => (Math.abs(offs[i] - off) < Math.abs(offs[SNAPS.indexOf(a)] - off) ? s : a), snap);
    go(target);
  };
  const handlers = {
    onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp,
    // a drag that started on a button must not also press it
    onClickCapture: (e: React.MouseEvent) => { if (dragged.current) { e.stopPropagation(); e.preventDefault(); } },
  };
  const cycle = () => { if (!dragged.current) go(snap === 'peek' ? 'half' : snap === 'half' ? 'full' : 'peek'); };
  const onKey = (e: RKeyboardEvent) => {
    const i = SNAPS.indexOf(snap), j = e.key === 'ArrowUp' ? Math.min(2, i + 1) : e.key === 'ArrowDown' ? Math.max(0, i - 1) : i;
    if (j !== i) { e.preventDefault(); go(SNAPS[j]); }
  };
  return { ref, snap, handlers, cycle, onKey };
}

