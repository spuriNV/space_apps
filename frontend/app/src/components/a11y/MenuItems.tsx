import Icon from '../Icons';
import { setPref, usePrefs, type LiteSetting, type Theme } from './prefs';
import { ax } from './ax';
import { t } from '../../i18n';
import LangToggle from '../../i18n/LangToggle';

function Switch({ checked, onChange, title, hint, testid }: { checked: boolean; onChange: (v: boolean) => void; title: string; hint: string; testid: string }) {
  return (
    <label className="mi-switch"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} data-testid={testid} /><span className="mi-track" aria-hidden="true" />
      <span><b>{title}</b><small>{hint}</small></span></label>
  );
}
function Radios<T extends string>({ name, legend, value, options, onChange, hint, testid }: { name: string; legend: string; value: T; options: { v: T; label: string }[]; onChange: (v: T) => void; hint?: string; testid: string }) {
  return (
    <fieldset className="mi-group" data-testid={testid}>
      <legend>{legend}</legend>
      <div className="mi-radios">
        {options.map((o) => <label key={o.v}><input type="radio" name={name} checked={value === o.v} onChange={() => onChange(o.v)} /><span>{o.label}</span></label>)}
      </div>
      {hint && <small>{hint}</small>}
    </fieldset>
  );
}

/** The Menu: one Accessibility section (every preference is remembered on this device), the list view, and the Accessibility page. */
export function MenuItems({ onList, onAbout, onShortcuts, onDone }: { onList: () => void; onAbout: () => void; onShortcuts: () => void; onDone: () => void }) {
  const prefs = usePrefs();
  return (
    <div className="menu-items" role="group" aria-label={t('ui.mi.menu')} data-testid="menu-items" onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); onDone(); } }}>
      <section className="mi-section mi-lang" aria-label="Language / Idioma" data-testid="lang-section">
        <h2 className="mi-h">Language · Idioma</h2>
        <LangToggle />
      </section>
      <section className="mi-section" aria-labelledby="mi-a11y-h" data-testid="a11y-section">
        <h2 id="mi-a11y-h" className="mi-h">{ax('section')}</h2>
        <Switch checked={prefs.simple} onChange={(v) => setPref('simple', v)} title={ax('simple')} hint={ax('simpleHint')} testid="simple-toggle" />
        <div className="mi-group">
          <label htmlFor="text-size"><b>{ax('textSize')}</b><output htmlFor="text-size" aria-live="off">{prefs.textPct}%</output></label>
          <input id="text-size" type="range" min={100} max={200} step={10} value={prefs.textPct} onChange={(e) => setPref('textPct', +e.target.value)} aria-valuetext={`${prefs.textPct}%`} data-testid="text-size" />
          <small>{ax('textSizeHint')}{prefs.textPct !== 100 && <> · <button type="button" className="link-btn" onClick={() => setPref('textPct', 100)}>{ax('reset')}</button></>}</small>
        </div>
        <Radios<Theme> name="theme" legend={ax('theme')} value={prefs.theme} onChange={(v) => setPref('theme', v)} testid="theme-group"
          options={[{ v: 'system', label: ax('themeSystem') }, { v: 'light', label: ax('themeLight') }, { v: 'dark', label: ax('themeDark') }]} />
        <Switch checked={prefs.dyslexia} onChange={(v) => setPref('dyslexia', v)} title={ax('dys')} hint={ax('dysHint')} testid="dys-toggle" />
        <Switch checked={prefs.outdoor} onChange={(v) => setPref('outdoor', v)} title={t('ui.a11y.s1b')} hint={t('ui.mi.outdoor_s')} testid="outdoor-toggle" />
        <Switch checked={prefs.pause} onChange={(v) => setPref('pause', v)} title={t('ui.a11y.s2b')} hint={t('ui.mi.pause_s')} testid="pause-toggle" />
        <Radios<LiteSetting> name="lite" legend={ax('lite')} value={prefs.lite} onChange={(v) => setPref('lite', v)} hint={prefs.liteNow && prefs.lite === 'auto' ? ax('liteNow') : ax('liteHint')} testid="lite-group"
          options={[{ v: 'auto', label: ax('liteAuto') }, { v: 'on', label: ax('liteOn') }, { v: 'off', label: ax('liteOff') }]} />
        <button className="mi-btn" onClick={() => { onDone(); onShortcuts(); }} data-testid="shortcuts-btn"><Icon name="info" size={20} /><span><b>{ax('shortcutsOpen')}</b><small>{ax('shortcutsHint')}</small></span></button>
      </section>
      <button className="mi-btn" onClick={() => { onDone(); onList(); }}><Icon name="fields" size={20} /><span><b>{t('ui.mi.list')}</b><small>{t('ui.mi.list_s')}</small></span></button>
      <button className="mi-btn" onClick={() => { onDone(); onAbout(); }} data-testid="about-a11y"><Icon name="info" size={20} /><span><b>{t('ui.a11y')}</b><small>{t('ui.mi.a11y_s')}</small></span></button>
    </div>
  );
}
