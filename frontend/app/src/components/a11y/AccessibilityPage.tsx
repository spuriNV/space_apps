import { Dialog } from './Dialog';
import Icon from '../Icons';
import { DisabilityHelp } from '../help/DisabilityHelp';
import { setPref, usePrefs, type Theme } from './prefs';
import { lang, setLang } from '../../i18n';
import './a11y-page.css';

const t = (en: string, es: string) => (lang === 'es' ? es : en);

function Row({ id, title, hint, checked, onChange }: { id: string; title: string; hint: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="mi-switch ap-row"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} data-testid={id} /><span className="mi-track" aria-hidden="true" />
      <span><b>{title}</b><small>{hint}</small></span></label>
  );
}

function QuickSettings() {
  const p = usePrefs();
  const themes: [Theme, string][] = [['light', t('Light', 'Claro')], ['dark', t('Dark', 'Oscuro')]];
  const reset = () => { setPref('outdoor', false); setPref('pause', false); setPref('simple', false); setPref('dyslexia', false); setPref('textPct', 100); setPref('theme', 'light'); setPref('lite', 'auto'); };
  return (
    <section className="ap-card ap-quick" aria-labelledby="ap-q" data-testid="a11y-quick">
      <h3 id="ap-q">{t('Quick settings', 'Ajustes rápidos')}</h3>
      <p className="ap-note">{t('Changes apply right away and are remembered on this device.', 'Los cambios se aplican al instante y se recuerdan en este dispositivo.')}</p>
      <div className="ap-field">
        <span id="ap-lang-l" className="ap-lbl">{t('Language', 'Idioma')}</span>
        <div className="seg full" role="radiogroup" aria-labelledby="ap-lang-l" data-testid="ap-lang">
          <button type="button" role="radio" lang="en" aria-checked={lang === 'en'} onClick={() => setLang('en')}>English</button>
          <button type="button" role="radio" lang="es" aria-checked={lang === 'es'} onClick={() => setLang('es')}>Español</button>
        </div>
      </div>
      <Row id="ap-outdoor" title={t('Outdoor / high contrast', 'Exterior / alto contraste')} hint={t('Bigger, bolder type for bright sun', 'Letra más grande y fuerte para el sol')} checked={p.outdoor} onChange={(v) => setPref('outdoor', v)} />
      <div className="ap-field">
        <span id="ap-theme-l" className="ap-lbl">{t('Theme', 'Tema')}</span>
        <div className="seg full" role="radiogroup" aria-labelledby="ap-theme-l" data-testid="ap-theme">
          {themes.map(([v, l]) => <button key={v} type="button" role="radio" aria-checked={p.theme === v} onClick={() => setPref('theme', v)}>{l}</button>)}
        </div>
      </div>
      <div className="ap-field">
        <label htmlFor="ap-size" className="ap-lbl">{t('Text size', 'Tamaño del texto')} <output htmlFor="ap-size">{p.textPct}%</output></label>
        <input id="ap-size" type="range" min={100} max={200} step={10} value={p.textPct} onChange={(e) => setPref('textPct', +e.target.value)} aria-valuetext={`${p.textPct}%`} data-testid="ap-size" />
        <p className="ap-preview" aria-hidden="true">{t('Preview: Rain is likely on Thursday.', 'Vista previa: se espera lluvia el jueves.')}</p>
      </div>
      <Row id="ap-dys" title={t('Easy-to-read type', 'Letra fácil de leer')} hint={t('Atkinson Hyperlegible, wider spacing', 'Atkinson Hyperlegible, más espacio')} checked={p.dyslexia} onChange={(v) => setPref('dyslexia', v)} />
      <Row id="ap-simple" title={t('Simple mode', 'Modo simple')} hint={t('One answer and one big button per step', 'Una respuesta y un botón grande por paso')} checked={p.simple} onChange={(v) => setPref('simple', v)} />
      <Row id="ap-pause" title={t('Pause all motion', 'Pausar todo movimiento')} hint={t('Stops replay, rain and fly-ins', 'Detiene repetición, lluvia y vuelos')} checked={p.pause} onChange={(v) => setPref('pause', v)} />
      <Row id="ap-lite" title={t('Lite mode', 'Modo ligero')} hint={t('No 3D or animation, fewer downloads', 'Sin 3D ni animación, menos descargas')} checked={p.liteNow} onChange={(v) => setPref('lite', v ? 'on' : 'off')} />
      <button type="button" className="btn btn-secondary ap-reset" onClick={reset} data-testid="ap-reset">{t('Reset to defaults', 'Restablecer valores')}</button>
    </section>
  );
}

function Card({ icon, title, children }: { icon: Parameters<typeof Icon>[0]['name']; title: string; children: React.ReactNode }) {
  const id = 'apc-' + title.replace(/\W+/g, '').toLowerCase();
  return (
    <section className="ap-card" aria-labelledby={id}>
      <h3 id={id}><span className="ap-ico" aria-hidden="true"><Icon name={icon} size={18} /></span>{title}</h3>
      {children}
    </section>
  );
}

const PHRASES: [string, string][] = [['open compare', 'abre comparar'], ['next step', 'siguiente paso'], ['read this week', 'lee esta semana'], ['go to my field', 've a mi campo'], ['describe my field', 'describir mi campo']];

export function AccessibilityPage({ onClose }: { onClose: () => void }) {
  const keys: [string, string][] = [
    ['1 – 5', t('Go to step 1 to 5', 'Ir al paso 1 al 5')], ['/', t('Find a field', 'Buscar un campo')], ['l', t('Open the list of fields', 'Abrir la lista de campos')],
    ['r', t('Read the answer aloud', 'Leer la respuesta en voz alta')], ['?', t('Show the shortcut list', 'Mostrar los atajos')], ['Esc', t('Close a pop-up', 'Cerrar una ventana')],
  ];
  return (
    <Dialog title={t('Accessibility', 'Accesibilidad')} onClose={onClose} testid="a11y-page" wide>
      <p className="ap-lead">{t('CropLytics works with a keyboard, a screen reader, a phone in bright sun and without colour. Change what you need below.', 'CropLytics funciona con teclado, lector de pantalla, un teléfono al sol y sin color. Cambie lo que necesite abajo.')}</p>
      <div className="ap-grid">
        <div className="ap-left"><QuickSettings /></div>
        <div className="ap-right">
          <div className="ap-cards">
            <Card icon="sat" title={t('See', 'Ver')}>
              <ul>
                <li>{t('High contrast for bright sun', 'Alto contraste para el sol')}</li>
                <li>{t('Dark mode that follows your device', 'Modo oscuro según su dispositivo')}</li>
                <li>{t('Text size from 100% to 200%', 'Texto del 100% al 200%')}</li>
                <li>{t('Colour-blind safe: ✓ OK, ~ Marginal, ✕ Too wet', 'Seguro para daltonismo: ✓ Bien, ~ Justo, ✕ Muy mojado')}</li>
                <li>{t('A list view of the map', 'Vista de lista del mapa')}</li>
                <li>{t('Chart summaries and tables', 'Resúmenes y tablas de los gráficos')}</li>
              </ul>
            </Card>
            <Card icon="mic" title={t('Hear and speak', 'Oír y hablar')}>
              <ul>
                <li>{t('Read aloud under the main answers', 'Leer en voz alta bajo las respuestas')}</li>
                <li>{t('Describe my field, spoken and written', 'Describir mi campo, en voz y texto')}</li>
                <li>{t('Voice questions in every browser', 'Preguntas por voz en todos los navegadores')}</li>
                <li>{t('Voice commands, also in Spanish:', 'Comandos de voz, también en español:')}
                  <span className="ap-chips">{PHRASES.map(([en, es]) => <span className="chip neutral" key={en}>“{t(en, es)}”</span>)}</span></li>
                <li>{t('Visual alerts: nothing depends on sound', 'Alertas visuales: nada depende del sonido')}</li>
              </ul>
            </Card>
            <Card icon="compass" title={t('Move and type', 'Moverse y escribir')}>
              <ul>
                <li>{t('Full keyboard use, with a skip link', 'Todo con teclado, con enlace para saltar')}</li>
                <li>{t('Targets at least 48 px', 'Botones de al menos 48 px')}</li>
                <li>{t('Map buttons for every gesture', 'Botones del mapa para cada gesto')}</li>
              </ul>
            </Card>
            <Card icon="info" title={t('Understand', 'Entender')}>
              <ul>
                <li>{t('Simple mode: short answers, one big button', 'Modo simple: respuestas cortas, un botón grande')}</li>
                <li>{t('Tap a farming term to see what it means', 'Toque un término agrícola para ver su significado')}</li>
                <li>{t('One question per step', 'Una pregunta por paso')}</li>
                <li>{t('No time limits: nothing closes by itself', 'Sin límites de tiempo: nada se cierra solo')}</li>
              </ul>
            </Card>
            <Card icon="link" title={t('Slow connections', 'Conexiones lentas')}>
              <ul>
                <li>{t('Lite mode turns on by itself on Data Saver', 'El modo ligero se activa solo con ahorro de datos')}</li>
                <li>{t('The last field you opened works offline', 'El último campo abierto funciona sin conexión')}</li>
              </ul>
            </Card>
          </div>
          <section className="ap-card" aria-labelledby="ap-k" data-testid="a11y-keys">
            <h3 id="ap-k"><span className="ap-ico" aria-hidden="true"><Icon name="menu" size={18} /></span>{t('Keyboard shortcuts', 'Atajos de teclado')}</h3>
            <table className="ap-keys">
              <caption className="sr-only">{t('Keyboard shortcuts', 'Atajos de teclado')}</caption>
              <thead><tr><th scope="col">{t('Key', 'Tecla')}</th><th scope="col">{t('Does', 'Hace')}</th></tr></thead>
              <tbody>{keys.map(([k, d]) => <tr key={k}><th scope="row"><kbd>{k}</kbd></th><td>{d}</td></tr>)}</tbody>
            </table>
            <p className="ap-note">{t('Shortcuts are off while you type.', 'Los atajos se apagan mientras escribe.')}</p>
          </section>
          <DisabilityHelp />
          <section className="ap-card" aria-labelledby="ap-t">
            <h3 id="ap-t"><span className="ap-ico" aria-hidden="true"><Icon name="check" size={18} /></span>{t('How we checked it', 'Cómo lo comprobamos')}</h3>
            <p className="ap-badges"><span className="chip accent">WCAG 2.2 AA</span><span className="chip accent">axe: 0 serious issues</span><span className="chip accent">{t('Tested in 10 setups', 'Probado en 10 configuraciones')}</span></p>
            <p className="ap-note">{t('Setups: phone, dark, 200% text, outdoor, dyslexia font and more. Not yet tested with a panel of people who use assistive technology every day. If something does not work for you, tell us and we will fix it.', 'Configuraciones: teléfono, oscuro, texto al 200%, exterior, letra para dislexia y más. Aún no probado con un grupo de personas que usan tecnología de apoyo a diario. Si algo no le funciona, díganos y lo arreglaremos.')}</p>
          </section>
        </div>
      </div>
    </Dialog>
  );
}
