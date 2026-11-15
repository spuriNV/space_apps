// "Describe my field": a short spoken summary built from the location data and this week's forecast. It is shown as text and
// read aloud with the device voice where there is one. Also started by the voice command "describe my field".
import { useEffect, useRef, useState } from 'react';
import type { Location } from '../../types';
import { acres, cropKey, cropName, mainCrop, nearTown, place } from '../ui/shared';
import { useRoute } from '../week/useRoute';
import { canSpeak, speakText, stopSpeaking } from '../help/ReadAloud';
import { ax } from './ax';

interface WeekBits { irrigation?: { verdict?: string }; field_access?: { line?: string } }

/** "149 acres, 4 miles east of Williams, Colusa County. Rice in 7 of the last 10 years; left bare in 2022. This week: ..." */
export function describeText(loc: Location, week: string | null): string {
  const nt = nearTown(loc), pl = place(loc);
  const where = nt === pl || nt.includes(pl) ? pl : `${nt}, ${pl}`;
  const ys = Object.keys(loc.crop_history).map(Number).sort().slice(-10);
  const parts: string[] = [ax('fieldPart', { acres: acres(loc), where })];
  if (ys.length) {
    const main = mainCrop(loc), n = ys.filter((y) => cropName(loc.crop_history[y]) === main).length;
    const bare = ys.filter((y) => cropKey(loc.crop_history[y]) === 'Left fallow');
    const bits = [n ? ax('ricePart', { crop: main, n, total: ys.length }) : '', bare.length ? (bare.length === 1 ? ax('fallowPart', { y: bare[0] }) : ax('fallowParts', { ys: bare.join(', ') })) : ''].filter(Boolean);
    if (bits.length) parts.push(`${bits.join('; ')}.`);
  }
  parts.push(week ? ax('weekPart', { text: week }) : ax('noWeekPart'));
  return parts.join(' ');
}

export function DescribeField({ loc }: { loc: Location }) {
  const [open, setOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const spoken = useRef('');
  const sp = loc.spot;
  const st = useRoute<WeekBits>(open && !(sp && sp.state !== 'ready') ? `/locations/${loc.id}/this_week` : null);
  const settled = st.kind === 'ok' || st.kind === 'missing' || st.kind === 'error' || st.kind === 'busy' || (sp && sp.state !== 'ready');
  const week = st.kind === 'ok' ? [st.data.irrigation?.verdict, st.data.field_access?.line].filter(Boolean).join(' ') : null;
  const text = open && settled ? describeText(loc, week) : '';
  useEffect(() => { setOpen(false); setSpeaking(false); spoken.current = ''; stopSpeaking(); }, [loc.id]);
  useEffect(() => { const f = () => { spoken.current = ''; setOpen(true); }; window.addEventListener('croplytics:describe', f); return () => window.removeEventListener('croplytics:describe', f); }, []);
  useEffect(() => {
    if (!text || spoken.current === text) return;
    spoken.current = text;
    if (canSpeak()) { setSpeaking(true); speakText(text, () => setSpeaking(false)); }
  }, [text]);
  useEffect(() => () => stopSpeaking(), []);
  const press = () => {
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    spoken.current = ''; // read it again
    if (open && text && canSpeak()) { spoken.current = text; setSpeaking(true); speakText(text, () => setSpeaking(false)); } else setOpen(true);
  };
  return (
    <div className="describe simple-keep" data-testid="describe">
      <button type="button" className="btn btn-secondary" onClick={press} aria-expanded={open} aria-controls="describe-text" data-testid="describe-btn">
        <span aria-hidden="true">{speaking ? '⏹' : '🔊'}</span>{speaking ? ax('describeStop') : ax('describe')}
      </button>
      {open && <p id="describe-text" className="describe-text" data-testid="describe-text">{text || '…'}</p>}
    </div>
  );
}
