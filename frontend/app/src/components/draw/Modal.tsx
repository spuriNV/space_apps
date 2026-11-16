// A rounded dialog over a soft scrim: pops in (opacity and a small scale, from its own centre), Esc and a tap on the scrim
// close it, Tab stays inside, and focus goes back to where it was. Used for naming, deleting and adding a shared field.
import { useEffect, useRef, type ReactNode } from 'react';
import { useBackClose } from '../../useBackClose';

export function Modal({ title, onClose, children, testid }: { title: string; onClose: () => void; children: ReactNode; testid?: string }) {
  const box = useRef<HTMLDivElement>(null);
  useBackClose(true, onClose);
  const was = useRef<Element | null>(null);
  useEffect(() => {
    was.current = document.activeElement;
    const el = box.current;
    (el?.querySelector<HTMLElement>('[data-autofocus]') ?? el?.querySelector<HTMLElement>('button, input'))?.focus();
    return () => { (was.current as HTMLElement | null)?.focus?.(); };
  }, []);
  const key = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { e.stopPropagation(); onClose(); return; }
    if (e.key !== 'Tab') return;
    const f = [...(box.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input, [href], [tabindex]:not([tabindex="-1"])') ?? [])];
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  return (
    <div className="dlg-scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }} onKeyDown={key}>
      <div className="dlg" role="dialog" aria-modal="true" aria-label={title} ref={box} data-testid={testid}>
        <h2 className="dlg-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}
