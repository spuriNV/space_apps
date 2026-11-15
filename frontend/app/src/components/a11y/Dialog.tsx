// A modal dialog: focus moves in, Tab stays inside, Escape closes, focus returns to what opened it.
import { useEffect, useRef, type ReactNode } from 'react';
import Icon from '../Icons';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, summary, [tabindex]:not([tabindex="-1"])';

export function Dialog({ title, onClose, children, testid }: { title: string; onClose: () => void; children: ReactNode; testid?: string }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    box.current?.querySelector<HTMLElement>('[data-autofocus]')?.focus();
    return () => prev?.focus?.();
  }, []);
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { e.stopPropagation(); onClose(); return; }
    if (e.key !== 'Tab') return;
    const f = [...(box.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])].filter((x) => x.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1], a = document.activeElement;
    if (e.shiftKey && (a === first || !box.current?.contains(a))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && (a === last || !box.current?.contains(a))) { e.preventDefault(); first.focus(); }
  };
  return (
    <div className="dlg-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }} onKeyDown={onKey}>
      <div className="dlg" role="dialog" aria-modal="true" aria-labelledby="dlg-title" ref={box} data-testid={testid}>
        <header><h2 id="dlg-title">{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close" data-autofocus><Icon name="close" size={20} /></button></header>
        <div className="dlg-body">{children}</div>
      </div>
    </div>
  );
}
