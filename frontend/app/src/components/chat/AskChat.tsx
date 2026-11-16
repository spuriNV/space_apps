// Ask CropLytics: a small chat popover from the top bar (backend app/chat). Built for screen readers first: the question box is
// labelled, each new answer is announced once through a polite live region, Escape closes and returns focus to the Ask
// button. Spoken input uses the browser's speech recognition where it exists; "Read answers aloud" (off by default, for people
// without a screen reader) and spoken questions use the server voice (speech.ts), else the device's voice. The phone keyboard's own mic works in the box as well.
import { useBackClose } from '../../useBackClose';
import { useEffect, useRef, useState } from 'react';
import { API_BASE, askChat, chatStatus, type ChatTurn } from '../../api';
import { Speaker } from './speech';
import Icon from '../Icons';
import { announce, onOtherOpen } from '../../overlays';
import { t, isEs, speechLang } from '../../i18n';
import { matchCommand } from '../a11y/ax';

interface Props { fieldId: string | null; fieldName: string | null; screen: string; date: string; waterLimit?: number | null }

const SUGGEST_FIELD = [t('ui.chat.sf1'), t('ui.chat.sf2'), t('ui.chat.sf3')];
const SUGGEST_NONE = [t('ui.chat.sn1'), t('ui.chat.sn2'), t('ui.chat.sn3')];
const SPEAK_KEY = 'croplytics.ask.speak';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SR: any = typeof window !== 'undefined' ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition : undefined;

const CAN_REC = typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';
const MAX_REC_S = 30;
function recMime() { for (const m of ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']) { try { if (MediaRecorder.isTypeSupported(m)) return m; } catch { /* old browser */ } } return ''; }

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
  const [rstate, setRstate] = useState<'idle' | 'recording' | 'transcribing'>('idle');
  const [secs, setSecs] = useState(0);
  const [level, setLevel] = useState(0);
  const forceRec = useRef(!SR); // set when native recognition is missing or its speech service is blocked (Firefox, Brave)
  const serverVoice = useRef(false);
  const speaker = useRef<Speaker | null>(null);
  speaker.current ??= new Speaker(() => serverVoice.current, () => setSpeaking(null));
  const sp = speaker.current;

  const stopSpeech = () => { sp.stop(); setSpeaking(null); };
  useBackClose(open, () => { setOpen(false); rec.current?.stop(); sp.stop(); setSpeaking(null); });
  const close = () => { setOpen(false); rec.current?.stop(); stopSpeech(); btn.current?.focus(); };
  useEffect(() => { chatStatus().then((s) => { serverVoice.current = s.tts; setEnabled(s.enabled); }); }, []);
  useEffect(() => { if (open) { input.current?.focus(); announce('ask'); } }, [open]);
  useEffect(() => onOtherOpen('ask', () => { setOpen(false); rec.current?.stop(); stopSpeech(); }), []); // eslint-disable-line react-hooks/exhaustive-deps
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
  useEffect(() => () => { rec.current?.stop(); sp.stop(); }, [sp]);

  if (!enabled) return null;


  const say = (text: string, idx: number) => { setSpeaking(idx); void sp.say(text); };

  /** byVoice: the question was spoken, so the answer is spoken back even with "Read answers aloud" off. */
  const send = async (text: string, byVoice = false) => {
    const question = text.trim().slice(0, 300);
    if (!question || busy) return;
    // a command ("open compare", "next step", "read this week", "go to my field", "describe my field"), in English or Spanish: do it, don't ask the chat API
    const cmd = matchCommand(question);
    if (cmd) { setQ(''); close(); window.dispatchEvent(new CustomEvent('croplytics:cmd', { detail: cmd })); return; }
    setQ(''); setErr(null); setBusy(true);
    setLive(t('ui.chat.thinking_live'));
    stopSpeech();
    if (!byVoice) sp.prime();
    const history = turns.slice(-6);
    setTurns((t) => [...t, { role: 'user', content: question }]);
    try {
      const a = await askChat({ question, history, field_id: fieldId, screen, date, water_limit: waterLimit ?? null });
      const idx = turns.length + 1; // after the question just added
      setTurns((t) => [...t, { role: 'assistant', content: a }]);
      if ((speak || byVoice) && sp.canSpeak) { setLive(t('ui.chat.ready')); say(a, idx); } // spoken here: don't make a screen reader read it a second time
      else setLive(t('ui.chat.says', { a }));
    } catch (e) {
      const m = e instanceof Error ? e.message : t('ui.chat.err');
      setErr(m); setLive(m);
      setTurns((t) => t.slice(0, -1)); setQ(question); // give the question back so it can be sent again
    } finally {
      setBusy(false);
    }
  };

  /** Fallback voice input: record with MediaRecorder, upload on stop to the local Whisper route, fill the box (never auto-send). */
  const recordClip = async () => {
    if (rstate === 'recording') { rec.current?.stop(); return; }
    if (rstate !== 'idle') return;
    stopSpeech(); setErr(null);
    let stream: MediaStream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) {
      const m = (e as DOMException)?.name === 'NotFoundError' ? t('ui.chat.nomic') : t('ui.chat.mic_blocked');
      setErr(m); setLive(m); return;
    }
    const mime = recMime();
    let mr: MediaRecorder;
    try { mr = new MediaRecorder(stream, mime ? { mimeType: mime, audioBitsPerSecond: 16000 } : undefined); }
    catch { stream.getTracks().forEach((t) => t.stop()); setErr(t('ui.chat.novoice')); return; }
    const chunks: Blob[] = [];
    let raf = 0, tick = 0, ctx: AudioContext | undefined;
    try {
      ctx = new AudioContext(); const an = ctx.createAnalyser(); an.fftSize = 512; ctx.createMediaStreamSource(stream).connect(an);
      const buf = new Uint8Array(an.fftSize);
      const loop = () => { an.getByteTimeDomainData(buf); let m = 0; for (const v of buf) m = Math.max(m, Math.abs(v - 128)); setLevel(Math.min(1, m / 64)); raf = requestAnimationFrame(loop); };
      loop();
    } catch { /* no meter */ }
    const t0 = Date.now();
    mr.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    mr.onstop = async () => {
      cancelAnimationFrame(raf); clearInterval(tick); void ctx?.close(); setLevel(0);
      stream.getTracks().forEach((t) => t.stop()); rec.current = null;
      if (Date.now() - t0 < 400 || !chunks.length) { setRstate('idle'); const m = t('ui.chat.nospeech'); setErr(m); setLive(m); return; }
      setRstate('transcribing'); setLive(t('merge.rec.transcribing'));
      try {
        const type = mr.mimeType || mime || 'audio/webm';
        const fd = new FormData(); fd.append('audio', new Blob(chunks, { type }), type.includes('mp4') ? 'clip.mp4' : 'clip.webm'); fd.append('language', isEs ? 'es' : 'en');
        const r = await fetch(`${API_BASE}/ask/transcribe`, { method: 'POST', body: fd });
        if (r.status === 501) throw new Error(t('merge.rec.no501'));
        if (r.status === 429) throw new Error(t('merge.rec.no429'));
        if (!r.ok) throw new Error(t('merge.rec.nottr'));
        const j = await r.json() as { text?: string };
        const tt = (j.text ?? '').trim();
        if (!tt) throw new Error(t('ui.chat.nospeech'));
        setQ(tt.slice(0, 300)); setLive(t('merge.rec.heard', { text: tt })); input.current?.focus();
      } catch (e) {
        const m = e instanceof TypeError ? t('merge.rec.noserver') : e instanceof Error ? e.message : t('merge.rec.fail');
        setErr(m); setLive(m);
      } finally { setRstate('idle'); }
    };
    rec.current = { stop: () => { if (mr.state !== 'inactive') mr.stop(); } };
    mr.start(); setRstate('recording'); setSecs(0); setLive(t('merge.rec.recording'));
    tick = window.setInterval(() => { const s = Math.floor((Date.now() - t0) / 1000); setSecs(s); if (s >= MAX_REC_S && mr.state !== 'inactive') mr.stop(); }, 250);
  };

  const listen = () => {
    if (forceRec.current || !SR) { void recordClip(); return; }
    if (listening) { rec.current?.stop(); return; }
    stopSpeech(); sp.prime();
    let r: any; // eslint-disable-line @typescript-eslint/no-explicit-any
    try { r = new SR(); } catch { if (CAN_REC) { forceRec.current = true; void recordClip(); } else setErr(t('ui.chat.novoice')); return; }
    r.lang = isEs ? speechLang : (navigator.language || 'en-US'); r.interimResults = true; r.maxAlternatives = 1;
    let final = '', latest = '', failed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (ev: any) => {
      let txt = '';
      for (let i = 0; i < ev.results.length; i++) { txt += ev.results[i][0].transcript; if (ev.results[i].isFinal) final = txt; }
      latest = txt; setQ(txt);
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onerror = (ev: any) => {
      const code = ev?.error as string | undefined;
      if (code === 'aborted') return;
      failed = true; setListening(false);
      if (CAN_REC && (code === 'network' || code === 'service-not-allowed' || code === 'not-allowed' || code === 'language-not-supported')) { forceRec.current = true; void recordClip(); return; }
      const m = code === 'not-allowed' || code === 'service-not-allowed' ? t('ui.chat.mic_blocked')
        : code === 'no-speech' ? t('ui.chat.nospeech')
        : code === 'audio-capture' ? t('ui.chat.nomic')
        : code === 'network' ? t('ui.chat.network')
        : t('ui.chat.nohear');
      setErr(m); setLive(m);
    };
    r.onend = () => { setListening(false); rec.current = null; const t = (final || latest).trim(); if (t && !failed) send(t, true); };
    rec.current = r;
    try { r.start(); setListening(true); setErr(null); setLive(t('ui.chat.listening_live')); }
    catch { rec.current = null; setErr(t('ui.chat.nostart')); }
  };

  const toggleSpeak = () => { const v = !speak; setSpeak(v); saveSpeak(v); if (!v) stopSpeech(); else sp.prime(); };
  const suggestions = fieldId ? SUGGEST_FIELD : SUGGEST_NONE;

  return (
    <div className="ask-wrap">
      <button ref={btn} className={`tb-ask ${open ? 'on' : ''}`} onClick={() => (open ? close() : setOpen(true))} aria-expanded={open} aria-controls="ask-pop" aria-label={t('ui.chat.ask')} data-testid="ask-btn">
        <Icon name="story" size={16} /><span className="tb-ask-label">{t('ui.chat.askshort')}</span>
      </button>
      {open && (
        <section id="ask-pop" className="ask-pop" role="dialog" aria-label={t('ui.chat.ask')} data-testid="ask-pop">
          <header className="ask-head">
            <h2>{t('ui.chat.ask')}</h2>
            <button className="icon-btn ghost" onClick={close} aria-label={t('ui.chat.close')}><Icon name="close" size={20} /></button>
          </header>
          <p className="ask-about">{fieldName ? <>{t('ui.chat.about')} <b>{fieldName}</b></> : t('ui.chat.aboutapp')}</p>

          <div ref={log} className="ask-log" role="log" aria-live="off" aria-label={t('ui.chat.conv')}>
            {turns.length === 0 && !busy && (
              <div className="ask-suggest" role="group" aria-label={t('ui.chat.suggested')}>
                {suggestions.map((s) => <button key={s} className="ask-chip" onClick={() => send(s)}>{s}</button>)}
              </div>
            )}
            {turns.map((turn, i) => (
              turn.role === 'user'
                ? <p key={i} className="ask-msg user"><span className="sr-only">{t('ui.chat.youasked')} </span>{turn.content}</p>
                : <div key={i} className="ask-msg assistant"><p><span className="sr-only">CropLytics: </span>{turn.content}</p>
                    {sp.canSpeak && <button type="button" className="ask-play" onClick={() => { if (speaking === i) stopSpeech(); else { sp.prime(); say(turn.content, i); } }} aria-label={speaking === i ? t('ui.chat.stopread') : t('ui.chat.readthis')}>
                      <Icon name={speaking === i ? 'pause' : 'play'} size={16} />{speaking === i ? t('ui.chat.stop') : t('ui.chat.listen')}</button>}
                  </div>
            ))}
            {busy && <p className="ask-msg assistant ask-busy" aria-hidden="true">{t('ui.chat.thinking')}</p>}
            {err && <p className="ask-err">{err}</p>}
          </div>
          {/* one polite announcement per answer; the log itself stays silent so nothing is read twice */}
          <div className="sr-only" aria-live="polite" aria-atomic="true">{live}</div>

          <form className="ask-form" onSubmit={(e) => { e.preventDefault(); send(q); }}>
            <label htmlFor="ask-q" className="sr-only">{t('ui.chat.yourq')}</label>
            <input id="ask-q" ref={input} value={q} onChange={(e) => setQ(e.target.value)} maxLength={300} placeholder={listening || rstate === 'recording' ? t('ui.chat.listening') : rstate === 'transcribing' ? t('merge.transcribing') : t('ui.chat.placeholder')} autoComplete="off" aria-busy={busy} />
            {(SR || CAN_REC) && <button type="button" className={`icon-btn ${listening || rstate === 'recording' ? 'rec' : ''}`} onClick={listen} aria-pressed={listening || rstate === 'recording'} aria-label={listening || rstate === 'recording' ? t('ui.chat.stoplisten') : t('ui.chat.byvoice')} disabled={busy || rstate === 'transcribing'}><Icon name="mic" size={20} /></button>}
            <button type="submit" className="icon-btn send" aria-label={t('ui.chat.send')} disabled={busy || !q.trim()}><Icon name="send" size={20} /></button>
          </form>
          {rstate !== 'idle' && <p className="ask-rec" role="status" style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0', fontSize: 13 }}>
            {rstate === 'recording'
              ? <><span aria-hidden="true" style={{ flex: '0 0 80px', height: 8, borderRadius: 4, background: 'rgba(128,128,128,.3)', overflow: 'hidden' }}><span style={{ display: 'block', height: '100%', width: `${Math.round(level * 100)}%`, background: 'currentColor' }} /></span>
                  Listening… 0:{String(secs).padStart(2, '0')} of 0:30. Tap the microphone to stop.</>
              : 'Transcribing…'}
          </p>}
          <div className="ask-foot">
            {sp.canSpeak && <button type="button" className="ask-speak" role="switch" aria-checked={speak} onClick={toggleSpeak}>
              <span className="ask-switch" aria-hidden="true" />{t('ui.chat.readall')}
            </button>}
            <p className="ask-hint">{SR || CAN_REC ? t('merge.hintMic') : t('ui.chat.hint_kb')}</p>
            <p>{t('ui.chat.disclaimer')}</p>
          </div>
        </section>
      )}
    </div>
  );
}
