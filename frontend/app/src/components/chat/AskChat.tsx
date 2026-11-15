// Ask CropLytics: a small chat popover from the top bar (backend app/chat). Built for screen readers first: the question box is
// labelled, each new answer is announced once through a polite live region, Escape closes and returns focus to the Ask
// button. Spoken input uses the browser's speech recognition where it exists; "Read answers aloud" (off by default, for people
// without a screen reader) uses the browser's speech. The phone keyboard's own mic works in the box as well.
import { useEffect, useRef, useState } from 'react';
import { askChat, chatEnabled, type ChatTurn } from '../../api';
import Icon from '../Icons';

interface Props { fieldId: string | null; fieldName: string | null; screen: string; date: string; waterLimit?: number | null }

const SUGGEST_FIELD = ['Describe this field', 'What do these numbers mean?', 'How do I compare rotations?'];
const SUGGEST_NONE = ['What is this app?', 'How do I pick a field?', 'How do I use this with a screen reader?'];
const SPEAK_KEY = 'croplytics.ask.speak';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SR: any = typeof window !== 'undefined' ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition : undefined;

const TTS: SpeechSynthesis | undefined = typeof window !== 'undefined' ? window.speechSynthesis : undefined;
/** A clear English voice: the OS's enhanced/natural voices first, else the default. Voices load late on some browsers, so ask each time. */
function pickVoice(): SpeechSynthesisVoice | undefined {
  const vs = TTS?.getVoices() ?? [];
  const en = vs.filter((v) => /^en[-_]US/i.test(v.lang));
  const pool = en.length ? en : vs.filter((v) => /^en/i.test(v.lang));
  return pool.find((v) => /natural|enhanced|premium|neural/i.test(v.name)) ?? pool.find((v) => /Google US English|Samantha|Aria|Jenny/i.test(v.name)) ?? pool.find((v) => v.default) ?? pool[0];
}
/** iOS and some browsers only allow speech that starts from a tap: speak nothing during the tap, then later speech is allowed. */
function primeSpeech() { try { if (TTS && !TTS.speaking) TTS.speak(new SpeechSynthesisUtterance('')); } catch { /* no speech */ } }

function loadSpeak() { try { return localStorage.getItem(SPEAK_KEY) === '1'; } catch { return false; } }
function saveSpeak(on: boolean) { try { localStorage.setItem(SPEAK_KEY, on ? '1' : '0'); } catch { /* private mode */ } }

export default function AskChat({ fieldId, fieldName, screen, date, waterLimit }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [live, setLive] = useState('');
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(loadSpeak);
  const [speaking, setSpeaking] = useState<number | null>(null); // index of the answer being read aloud
  const btn = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const rec = useRef<{ stop: () => void } | null>(null);

  const stopSpeech = () => { TTS?.cancel(); setSpeaking(null); };
  const close = () => { setOpen(false); rec.current?.stop(); stopSpeech(); btn.current?.focus(); };
  useEffect(() => { chatEnabled().then(setEnabled); }, []);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  // Escape closes from anywhere while open (focus may be on a chip or the switch, not only the box)
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', k);
    return () => document.removeEventListener('keydown', k);
  });
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight, behavior: 'smooth' }); }, [turns, busy]);
  // a new field starts a new conversation (the old answers were about the old field)
  useEffect(() => { setTurns([]); setErr(null); }, [fieldId]);
  useEffect(() => () => { rec.current?.stop(); TTS?.cancel(); }, []);

  if (!enabled) return null;


  const say = (text: string, idx: number) => {
    if (!TTS) return;
    TTS.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice(); if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'en-US';
    u.rate = 1; u.onend = u.onerror = () => setSpeaking((cur) => (cur === idx ? null : cur));
    setSpeaking(idx); TTS.speak(u);
  };

  /** byVoice: the question was spoken, so the answer is spoken back even with "Read answers aloud" off. */
  const send = async (text: string, byVoice = false) => {
    const question = text.trim().slice(0, 300);
    if (!question || busy) return;
    setQ(''); setErr(null); setBusy(true);
    setLive('Thinking.');
    stopSpeech();
    if (!byVoice) primeSpeech();
    const history = turns.slice(-6);
    setTurns((t) => [...t, { role: 'user', content: question }]);
    try {
      const a = await askChat({ question, history, field_id: fieldId, screen, date, water_limit: waterLimit ?? null });
      const idx = turns.length + 1; // after the question just added
      setTurns((t) => [...t, { role: 'assistant', content: a }]);
      if ((speak || byVoice) && TTS) { setLive('Answer ready.'); say(a, idx); } // spoken here: don't make a screen reader read it a second time
      else setLive(`CropLytics says: ${a}`);
    } catch (e) {
      const m = e instanceof Error ? e.message : 'The assistant could not answer. Please try again.';
      setErr(m); setLive(m);
      setTurns((t) => t.slice(0, -1)); setQ(question); // give the question back so it can be sent again
    } finally {
      setBusy(false);
    }
  };

  const listen = () => {
    if (!SR) return;
    if (listening) { rec.current?.stop(); return; }
    stopSpeech(); primeSpeech();
    const r = new SR();
    r.lang = 'en-US'; r.interimResults = true; r.maxAlternatives = 1;
    let final = '';
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (ev: any) => {
      let txt = '';
      for (let i = 0; i < ev.results.length; i++) { txt += ev.results[i][0].transcript; if (ev.results[i].isFinal) final = txt; }
      setQ(txt);
    };
    r.onerror = () => { setListening(false); setLive('Could not hear that. Try again or type your question.'); };
    r.onend = () => { setListening(false); rec.current = null; if (final.trim()) send(final, true); };
    rec.current = r; setListening(true); setLive('Listening. Ask your question.');
    r.start();
  };

  const toggleSpeak = () => { const v = !speak; setSpeak(v); saveSpeak(v); if (!v) stopSpeech(); else primeSpeech(); };
  const suggestions = fieldId ? SUGGEST_FIELD : SUGGEST_NONE;

  return (
    <div className="ask-wrap">
      <button ref={btn} className={`tb-ask ${open ? 'on' : ''}`} onClick={() => (open ? close() : setOpen(true))} aria-expanded={open} aria-controls="ask-pop" aria-label="Ask CropLytics" data-testid="ask-btn">
        <Icon name="story" size={16} /><span className="tb-ask-label">Ask</span>
      </button>
      {open && (
        <section id="ask-pop" className="ask-pop" role="dialog" aria-label="Ask CropLytics" data-testid="ask-pop">
          <header className="ask-head">
            <h2>Ask CropLytics</h2>
            <button className="icon-btn ghost" onClick={close} aria-label="Close Ask CropLytics"><Icon name="close" size={20} /></button>
          </header>
          <p className="ask-about">{fieldName ? <>About <b>{fieldName}</b></> : 'About the app. Pick a field to ask about its numbers.'}</p>

          <div ref={log} className="ask-log" role="log" aria-live="off" aria-label="Conversation">
            {turns.length === 0 && !busy && (
              <div className="ask-suggest" role="group" aria-label="Suggested questions">
                {suggestions.map((s) => <button key={s} className="ask-chip" onClick={() => send(s)}>{s}</button>)}
              </div>
            )}
            {turns.map((t, i) => (
              t.role === 'user'
                ? <p key={i} className="ask-msg user"><span className="sr-only">You asked: </span>{t.content}</p>
                : <div key={i} className="ask-msg assistant"><p><span className="sr-only">CropLytics: </span>{t.content}</p>
                    {TTS && <button type="button" className="ask-play" onClick={() => (speaking === i ? stopSpeech() : say(t.content, i))} aria-label={speaking === i ? 'Stop reading this answer' : 'Read this answer aloud'}>
                      <Icon name={speaking === i ? 'pause' : 'play'} size={16} />{speaking === i ? 'Stop' : 'Listen'}</button>}
                  </div>
            ))}
            {busy && <p className="ask-msg assistant ask-busy" aria-hidden="true">Thinking…</p>}
            {err && <p className="ask-err">{err}</p>}
          </div>
          {/* one polite announcement per answer; the log itself stays silent so nothing is read twice */}
          <div className="sr-only" aria-live="polite" aria-atomic="true">{live}</div>

          <form className="ask-form" onSubmit={(e) => { e.preventDefault(); send(q); }}>
            <label htmlFor="ask-q" className="sr-only">Your question</label>
            <input id="ask-q" ref={input} value={q} onChange={(e) => setQ(e.target.value)} maxLength={300} placeholder={listening ? 'Listening…' : 'Ask about this field or the app'} autoComplete="off" aria-busy={busy} />
            {SR && <button type="button" className={`icon-btn ${listening ? 'rec' : ''}`} onClick={listen} aria-pressed={listening} aria-label={listening ? 'Stop listening' : 'Ask by voice'} disabled={busy}><Icon name="mic" size={20} /></button>}
            <button type="submit" className="icon-btn send" aria-label="Send question" disabled={busy || !q.trim()}><Icon name="send" size={20} /></button>
          </form>
          <div className="ask-foot">
            {TTS && <button type="button" className="ask-speak" role="switch" aria-checked={speak} onClick={toggleSpeak}>
              <span className="ask-switch" aria-hidden="true" />Read every answer aloud
            </button>}
            <p className="ask-hint">{SR ? 'Ask by voice with the microphone and the answer is spoken back.' : 'Use your keyboard\'s microphone to ask by voice.'}</p>
            <p>AI answers from this field's data. Not advice. Questions go to DeepSeek; don't type personal details.</p>
          </div>
        </section>
      )}
    </div>
  );
}
