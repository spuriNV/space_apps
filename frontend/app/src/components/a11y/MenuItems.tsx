import Icon from '../Icons';
import { setPref, usePrefs } from './prefs';
import { t } from '../../i18n';

/** The Menu: display preferences (remembered), the list view, and the Accessibility page. */
export function MenuItems({ onList, onAbout, onDone }: { onList: () => void; onAbout: () => void; onDone: () => void }) {
  const prefs = usePrefs();
  return (
    <div className="menu-items" role="group" aria-label={t('ui.mi.menu')} data-testid="menu-items" onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); onDone(); } }}>
      <label className="mi-switch"><input type="checkbox" checked={prefs.outdoor} onChange={(e) => setPref('outdoor', e.target.checked)} data-testid="outdoor-toggle" /><span className="mi-track" aria-hidden="true" />
        <span><b>{t('ui.a11y.s1b')}</b><small>{t('ui.mi.outdoor_s')}</small></span></label>
      <label className="mi-switch"><input type="checkbox" checked={prefs.pause} onChange={(e) => setPref('pause', e.target.checked)} data-testid="pause-toggle" /><span className="mi-track" aria-hidden="true" />
        <span><b>{t('ui.a11y.s2b')}</b><small>{t('ui.mi.pause_s')}</small></span></label>
      <button className="mi-btn" onClick={() => { onDone(); onList(); }}><Icon name="fields" size={20} /><span><b>{t('ui.mi.list')}</b><small>{t('ui.mi.list_s')}</small></span></button>
      <button className="mi-btn" onClick={() => { onDone(); onAbout(); }} data-testid="about-a11y"><Icon name="info" size={20} /><span><b>{t('ui.a11y')}</b><small>{t('ui.mi.a11y_s')}</small></span></button>
    </div>
  );
}
