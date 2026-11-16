// Strings and small helpers for the second batch of access features (Simple mode, voice commands, shortcuts, alerts...).
// Every string has an English and a Spanish version; ax(key) picks by the page language.
const EN = {
  section: 'Accessibility',
  simple: 'Simple mode', simpleHint: 'One answer and one big button per step',
  textSize: 'Text size', textSizeHint: 'Makes all text larger, 100% to 200%', reset: 'Reset',
  theme: 'Colours', themeSystem: 'Same as device', themeLight: 'Light', themeDark: 'Dark',
  dys: 'Easy-to-read type', dysHint: 'Atkinson Hyperlegible, wider spacing',
  lite: 'Lite mode', liteAuto: 'Automatic', liteOn: 'On', liteOff: 'Off', liteHint: 'No 3D or animation, fewer downloads. Automatic on a slow or Data Saver connection.', liteNow: 'Lite mode is on because the connection is slow or Data Saver is on.',
  showMore: 'Show more', showLess: 'Show less',
  describe: 'Describe my field', describeStop: 'Stop reading', describeHint: 'Hear a short summary of this field',
  largePrint: 'Large print', largePrintHint: 'The page prints at 18 point or larger, in black on white',
  alertTitle: 'Weather alert', tooWet: 'Too wet to work the field', tooWetDay: 'Too wet to work the field {when}.',
  alertAnnounce: 'Alert for this field: {text}',
  shortcuts: 'Keyboard shortcuts', shortcutsOpen: 'Keyboard shortcuts', shortcutsHint: 'Press ? any time. Shortcuts are off while you type.',
  kStep: 'Go to step 1 to 5', kSearch: 'Find a field', kList: 'Open the list of fields', kRead: 'Read the answer aloud', kHelp: 'Show this list', kEsc: 'Close a pop-up', kPanel: 'Hide or show the side panel',
  glossClose: 'Close', glossFor: 'What {term} means',
  cmdDone: 'Done: {what}.', cmdCompare: 'opening Compare', cmdNext: 'going to the next step', cmdWeek: 'reading this week', cmdField: 'going to your field', cmdDescribe: 'describing your field',
  cmdNeedField: 'Pick a field first.', cmdLast: 'You are already on the last step.',
  noWeek: 'There is no weather summary for this field yet.',
  fieldPart: '{acres} acres, {where}.', ricePart: '{crop} in {n} of the last {total} years', fallowPart: 'left bare in {y}', fallowParts: 'left bare in {ys}', weekPart: 'This week: {text}', noWeekPart: 'The week ahead is not loaded yet.', ready: 'Ready.',
  offline: 'No connection. Showing the last field you opened.',
  liteBadge: 'Lite mode',
  footnoteTime: 'Nothing here times out. Pop-ups stay open until you close them.',
} as const;
type Key = keyof typeof EN;
const ES: Record<Key, string> = {
  section: 'Accesibilidad',
  simple: 'Modo simple', simpleHint: 'Una respuesta y un botón grande por paso',
  textSize: 'Tamaño del texto', textSizeHint: 'Agranda todo el texto, del 100% al 200%', reset: 'Restablecer',
  theme: 'Colores', themeSystem: 'Igual que el dispositivo', themeLight: 'Claro', themeDark: 'Oscuro',
  dys: 'Letra fácil de leer', dysHint: 'Atkinson Hyperlegible, con más espacio',
  lite: 'Modo ligero', liteAuto: 'Automático', liteOn: 'Sí', liteOff: 'No', liteHint: 'Sin 3D ni animación, menos descargas. Automático con conexión lenta o ahorro de datos.', liteNow: 'El modo ligero está activo porque la conexión es lenta o el ahorro de datos está activado.',
  showMore: 'Ver más', showLess: 'Ver menos',
  describe: 'Describir mi campo', describeStop: 'Dejar de leer', describeHint: 'Escuche un resumen corto de este campo',
  largePrint: 'Letra grande', largePrintHint: 'La página se imprime en 18 puntos o más, en negro sobre blanco',
  alertTitle: 'Alerta del tiempo', tooWet: 'Demasiado mojado para trabajar el campo', tooWetDay: 'Demasiado mojado para trabajar el campo {when}.',
  alertAnnounce: 'Alerta para este campo: {text}',
  shortcuts: 'Atajos de teclado', shortcutsOpen: 'Atajos de teclado', shortcutsHint: 'Pulse ? en cualquier momento. Los atajos se apagan mientras escribe.',
  kStep: 'Ir al paso 1 al 5', kSearch: 'Buscar un campo', kList: 'Abrir la lista de campos', kRead: 'Leer la respuesta en voz alta', kHelp: 'Mostrar esta lista', kEsc: 'Cerrar una ventana', kPanel: 'Ocultar o mostrar el panel lateral',
  glossClose: 'Cerrar', glossFor: 'Qué significa {term}',
  cmdDone: 'Listo: {what}.', cmdCompare: 'abriendo Comparar', cmdNext: 'pasando al paso siguiente', cmdWeek: 'leyendo esta semana', cmdField: 'yendo a su campo', cmdDescribe: 'describiendo su campo',
  cmdNeedField: 'Primero elija un campo.', cmdLast: 'Ya está en el último paso.',
  noWeek: 'Todavía no hay resumen del tiempo para este campo.',
  fieldPart: '{acres} acres, {where}.', ricePart: '{crop} en {n} de los últimos {total} años', fallowPart: 'sin sembrar en {y}', fallowParts: 'sin sembrar en {ys}', weekPart: 'Esta semana: {text}', noWeekPart: 'El pronóstico todavía no se ha cargado.', ready: 'Listo.',
  offline: 'Sin conexión. Se muestra el último campo que abrió.',
  liteBadge: 'Modo ligero',
  footnoteTime: 'Nada aquí caduca. Las ventanas siguen abiertas hasta que las cierre.',
};
export const lang = () => (((typeof document !== 'undefined' && document.documentElement.lang) || (typeof navigator !== 'undefined' && navigator.language) || 'en').toLowerCase().startsWith('es') ? 'es' : 'en');
export function ax(key: Key, vars?: Record<string, string | number>): string {
  let s: string = (lang() === 'es' ? ES : EN)[key];
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}

// ---------- a live region for messages that are not tied to one control ----------
let liveEl: HTMLElement | null = null;
export function setLiveRegion(el: HTMLElement | null) { liveEl = el; }
/** Announce to screen readers (polite) without moving focus. Clears first so the same text is read twice if asked twice. */
export function say(text: string, assertive = false) {
  if (!liveEl) return;
  liveEl.setAttribute('aria-live', assertive ? 'assertive' : 'polite');
  liveEl.textContent = '';
  window.setTimeout(() => { if (liveEl) liveEl.textContent = text; }, 40);
}

// ---------- voice and typed commands: a small intent matcher that runs before a question goes to the chat API ----------
export type Command = 'compare' | 'next' | 'readweek' | 'myfield' | 'describe';
const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
const PATTERNS: [Command, RegExp][] = [
  // describe first: "describe my field" must not match "go to my field"
  ['describe', /^(please )?(describe|tell me about|read) (my|the|this) (field|farm|land)$|^(describe|describa|describir) (mi|el|este) (campo|terreno|parcela)$|^(describeme|descríbeme|describame) (mi |el )?(campo|terreno)?$/],
  ['readweek', /^(please )?(read|say|tell me) (this|the) week$|^read (this|the) (weeks?|forecast)$|^(lee|leer|lea|dime|dígame|digame) (esta|la) semana$|^(lee|leer|lea) (el )?(pronostico|tiempo)$/],
  ['compare', /^(please )?(open|show|go to|take me to) (the )?compare( rotations)?$|^compare$|^(abre|abrir|abra|muestra|muestre|ve a|ir a|ir al|ve al) (el )?(paso )?(comparar|comparacion)$/],
  ['next', /^(please )?(next( step)?|go next|go to the next step|continue|next page)$|^(siguiente|siguiente paso|paso siguiente|ve al siguiente paso|ir al siguiente paso|continua|continuar|adelante)$/],
  ['myfield', /^(please )?(go to|open|show|take me to|back to) (my|the) field$|^(my field|field now)$|^(ve a|ir a|abre|abrir|muestra|muestrame|llevame a) (mi|el) (campo|terreno)$/],
];
/** The command in what the person said or typed, or null when it is a question for the assistant. */
export function matchCommand(text: string): Command | null {
  const t = norm(text);
  if (!t || t.split(' ').length > 8) return null;
  for (const [c, re] of PATTERNS) if (re.test(t)) return c;
  return null;
}

// ---------- Easy-read: the first short sentence ----------
/** Easy-read form of an answer line: no brackets, the first sentence only, long ones cut at a comma or "with". */
export function easy(text: string): string {
  let t = text.replace(/\s*\([^)]*\)/g, '').replace(/\s+/g, ' ').trim();
  const first = t.match(/^.*?[.!?](?=\s|$)/)?.[0] ?? t;
  t = first;
  if (t.split(' ').length > 22) { const cut = t.split(/,\s|;\s|\swith\s|\sand\s/)[0]; if (cut.split(' ').length >= 5) t = cut.replace(/[.,;]$/, '') + '.'; }
  return t;
}
