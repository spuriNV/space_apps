import { lang, setLang, t } from './index';

/** "English / Español" switch for the top bar (desktop) and the Menu (phone). */
export default function LangToggle() {
  return (
    <div className="lang-toggle" role="group" aria-label={t('lang.label')} data-testid="lang-toggle">
      <button type="button" className={lang === 'en' ? 'on' : ''} aria-pressed={lang === 'en'} lang="en" onClick={() => setLang('en')} data-testid="lang-en">English</button>
      <span aria-hidden="true">/</span>
      <button type="button" className={lang === 'es' ? 'on' : ''} aria-pressed={lang === 'es'} lang="es" onClick={() => setLang('es')} data-testid="lang-es">Español</button>
    </div>
  );
}
