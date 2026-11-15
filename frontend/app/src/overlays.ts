// One overlay at a time: Map layers, Ask and Draw close each other. A component calls announce('ask') when it opens and
// subscribes with onOtherOpen to close itself when a different one opens.
export type Overlay = 'layers' | 'ask' | 'draw';
const bus = new EventTarget();
export const announce = (name: Overlay) => bus.dispatchEvent(new CustomEvent<Overlay>('overlay', { detail: name }));
export function onOtherOpen(me: Overlay, close: () => void) {
  const h = (e: Event) => { if ((e as CustomEvent<Overlay>).detail !== me) close(); };
  bus.addEventListener('overlay', h);
  return () => bus.removeEventListener('overlay', h);
}
