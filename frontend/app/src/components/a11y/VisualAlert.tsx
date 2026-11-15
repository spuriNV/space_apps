// Visual alerts: a prominent banner for NWS alerts and for "too wet to work the field". It never relies on sound or colour
// alone (an icon and words), stays until the situation changes, and is announced once to screen readers through a live region.
import { useEffect } from 'react';
import { ax, say } from './ax';
import { t } from '../../i18n';

export interface AlertInfo { events: { text: string; url?: string }[]; wet: string | null }
export function VisualAlert({ info }: { info: AlertInfo }) {
  const text = [...info.events.map((e) => e.text), ...(info.wet ? [info.wet] : [])].join('. ');
  useEffect(() => { if (text) say(ax('alertAnnounce', { text }), true); }, [text]);
  if (!text) return null;
  return (
    <div className="va" role="group" aria-label={ax('alertTitle')} data-testid="visual-alert">
      {info.events.map((e, i) => (
        <p key={i} className="va-item warn"><i aria-hidden="true">!</i><span><b>{ax('alertTitle')}</b> {e.text}{e.url && <> · <a href={e.url} target="_blank" rel="noreferrer">{t('week.nws')}</a></>}</span></p>
      ))}
      {info.wet && <p className="va-item wet" data-testid="va-wet"><i aria-hidden="true">✕</i><span><b>{info.wet}</b></span></p>}
    </div>
  );
}
