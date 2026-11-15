// "Read aloud": speaks a short plain-language text with the browser's own speechSynthesis (free; Chrome, Safari, Edge).
// Hidden where it is unsupported. One voice at a time; a second press stops it. Not used for the long Ask answers,
// which have their own Listen control.
import { useEffect, useRef, useState } from 'react';
import { deviceVoice } from '../chat/speech';
import { isEs, speechLang, t } from '../../i18n';

const TTS: SpeechSynthesis | undefined = typeof window !== 'undefined' ? window.speechSynthesis : undefined;
let stopCurrent: (() => void) | null = null;

function voiceFor(lang: string): SpeechSynthesisVoice | undefined {
  const vs = TTS?.getVoices() ?? [];
  const l = lang.toLowerCase();
  return vs.find((v) => v.lang.toLowerCase().replace('_', '-') === l) ?? vs.find((v) => v.lang.toLowerCase().startsWith(l.split('-')[0]));
}
/** Plain text for speech: no markup characters, arrows or double spaces. */
export const speakable = (t: string) => t.replace(/[*_`#→·]/g, ' ').replace(/\s+/g, ' ').trim();

export function ReadAloud({ text, label = t('merge.readAloud') }: { text: string; label?: string }) {
  const [on, setOn] = useState(false);
  const me = useRef<() => void>(() => {});
  const stop = () => { TTS?.cancel(); setOn(false); if (stopCurrent === me.current) stopCurrent = null; };
  me.current = stop;
  useEffect(() => () => { if (stopCurrent === me.current) { TTS?.cancel(); stopCurrent = null; } }, []);
  useEffect(() => { if (on) stop(); }, [text]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!TTS || typeof SpeechSynthesisUtterance === 'undefined' || !speakable(text)) return null;
  const toggle = () => {
    if (on) return stop();
    stopCurrent?.(); TTS.cancel();
    const lang = isEs ? speechLang : navigator.language || 'en-US';
    const u = new SpeechSynthesisUtterance(speakable(text));
    u.lang = lang; u.rate = 0.95;
    const v = isEs ? deviceVoice() : voiceFor(lang); if (v && isEs) u.lang = v.lang; if (v) u.voice = v;
    u.onend = u.onerror = () => { setOn(false); if (stopCurrent === me.current) stopCurrent = null; };
    stopCurrent = me.current; setOn(true); TTS.speak(u);
  };
  return (
    <button type="button" className="ra" aria-pressed={on} onClick={toggle} data-testid="read-aloud">
      <span aria-hidden="true">{on ? '⏹' : '🔊'}</span>{on ? t('merge.stop') : label}
    </button>
  );
}
