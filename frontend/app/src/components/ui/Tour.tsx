// The example field's 4-stop guided tour: small anchored pop-cards, Next / Skip, a progress dot row.
// Keyboard: focus moves into the card, Esc skips. Static cards only (no motion). Dismissal is remembered in localStorage.
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { t } from '../../i18n';

function usePhone() {
  const q = '(max-width: 640px)';
  const [m, setM] = useState(() => window.matchMedia(q).matches);
  useEffect(() => { const mq = window.matchMedia(q); const f = () => setM(mq.matches); mq.addEventListener('change', f); return () => mq.removeEventListener('change', f); }, []);
  return m;
}

const KEY = 'croplytics.tour.done';
export const tourDismissed = () => { try { return localStorage.getItem(KEY) === '1'; } catch { return false; } };
const remember = () => { try { localStorage.setItem(KEY, '1'); } catch { /* private mode: fine */ } };

export const TOUR_STOPS: { step: 'now' | 'compare' | 'brief'; sel: string; title: string; text: string }[] = [
  { step: 'now', sel: '[data-testid="this-week"]', title: t('tour.0.title'), text: t('tour.0.text') },
  { step: 'now', sel: '[data-testid="step-year"]', title: t('tour.1.title'), text: t('tour.1.text') },
  { step: 'compare', sel: '[data-testid="water-bars"]', title: t('tour.2.title'), text: t('tour.2.text') },
  { step: 'brief', sel: '[data-testid="print"]', title: t('tour.3.title'), text: t('tour.3.text') },
];

export default function Tour(p: { idx: number; go: (i: number) => void; canReplay: boolean; onReplay: () => void; onClose: () => void }) {
  const stop = TOUR_STOPS[p.idx], last = p.idx === TOUR_STOPS.length - 1;
  const phone = usePhone();
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [bottom, setBottom] = useState<number | null>(null);
  const done = () => { remember(); p.onClose(); };

  // find the anchor (it may mount a moment after the step changes), outline it, place the card beside it
  useLayoutEffect(() => {
    let el: HTMLElement | null = null, tries = 0, timer = 0;
    const place = () => {
      const card = ref.current; if (!card) return;
      const r = el?.getBoundingClientRect();
      const tabs = document.querySelector('.mob-tabs')?.getBoundingClientRect();
      setBottom(phone && tabs ? Math.max(8, Math.round(window.innerHeight - tabs.top + 8)) : null);
      if (!r || phone) { setPos(null); return; }
      const w = card.offsetWidth, h = card.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
      let left = r.right + 14, top = r.top;
      if (left + w > vw - 12) { left = Math.min(Math.max(12, r.left), vw - w - 12); top = r.bottom + 10; }
      setPos({ left, top: Math.min(Math.max(70, top), vh - h - 12) });
    };
    const find = () => {
      el = document.querySelector<HTMLElement>(stop.sel);
      if (el) { el.classList.add('tour-on'); el.scrollIntoView({ block: phone ? 'start' : 'nearest' }); place(); }
      else { place(); if (tries++ < 40) timer = window.setTimeout(find, 250); }
    };
    setPos(null); find();
    const onResize = () => place();
    window.addEventListener('resize', onResize);
    return () => { window.clearTimeout(timer); window.removeEventListener('resize', onResize); el?.classList.remove('tour-on'); };
  }, [p.idx, phone, stop.sel]);

  useEffect(() => { ref.current?.querySelector<HTMLElement>('[data-tour-next]')?.focus(); }, [p.idx]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopPropagation(); done(); } };
    document.addEventListener('keydown', k, true);
    return () => document.removeEventListener('keydown', k, true);
  });

  return (
    <div ref={ref} className={`tour-card ${pos ? 'anch' : ''}`} role="dialog" aria-label={t('tour.aria', { n: p.idx + 1, total: TOUR_STOPS.length })} data-testid="tour" style={pos ? { top: pos.top, left: pos.left } : phone && bottom != null ? { bottom } : undefined}>
      <b className="tour-h">{stop.title}</b>
      <p>{stop.text}</p>
      <div className="tour-row">
        <span className="tour-dots" aria-hidden="true">{TOUR_STOPS.map((_, i) => <i key={i} className={i === p.idx ? 'on' : ''} />)}</span>
        <span className="tour-act">
          {p.idx === 1 && p.canReplay && <button className="btn btn-outline btn-sm" onClick={() => { p.onReplay(); }} data-testid="tour-replay">{t('tour.replay')}</button>}
          <button className="btn btn-text btn-sm" onClick={done} data-testid="tour-skip">{last ? t('tour.close') : t('tour.skip')}</button>
          {!last && <button className="btn btn-primary btn-sm" data-tour-next onClick={() => p.go(p.idx + 1)} data-testid="tour-next">{t('tour.next')}</button>}
          {last && <button className="btn btn-primary btn-sm" data-tour-next onClick={done} data-testid="tour-done">{t('tour.done')}</button>}
        </span>
      </div>
    </div>
  );
}
