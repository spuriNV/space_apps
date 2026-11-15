import { createContext, useContext, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const BottomEl = createContext<HTMLElement | null>(null);

export function DockProvider({ el, children }: { el: HTMLElement | null; children: ReactNode }) {
  return <BottomEl.Provider value={el}>{children}</BottomEl.Provider>;
}

/** Renders children into the bottom dock under the map. */
export function DockBottom({ children }: { children: ReactNode }) {
  const el = useContext(BottomEl);
  if (!el) return null;
  return createPortal(children, el);
}
