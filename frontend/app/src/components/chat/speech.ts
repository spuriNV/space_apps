// Spoken answers for Ask CropLytics. Server voice first (POST /api/tts: Kokoro, a gentle female voice, the same on every
// device), one sentence at a time with the next one fetched while the current one plays, so speech starts quickly. If the
// server has no voice or a request fails, the rest of the answer is read by the device's own voice.
import { API_BASE } from '../../api';

const TTS: SpeechSynthesis | undefined = typeof window !== 'undefined' ? window.speechSynthesis : undefined;
// 0.05 s of silence: played during a tap so iOS and other browsers allow the later, non-tap playback
const SILENT = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=';

/** Sentences of at most ~380 characters; very short ones join the next so the voice does not stop and start. */
export function sentences(text: string): string[] {
  const raw = text.replace(/\s+/g, ' ').match(/[^.!?]+[.!?]+["')\]]*\s*|[^.!?]+$/g) ?? [text];
  const out: string[] = [];
  for (const s of raw.map((x) => x.trim()).filter(Boolean)) {
    const last = out[out.length - 1];
    if (last && (last.length < 40 || s.length < 25) && last.length + s.length < 380) out[out.length - 1] = `${last} ${s}`;
    else out.push(s.length > 380 ? s.slice(0, 380) : s);
  }
  return out;
}

function deviceVoice(): SpeechSynthesisVoice | undefined {
  const vs = TTS?.getVoices() ?? [];
  const en = vs.filter((v) => /^en[-_]US/i.test(v.lang));
  const pool = en.length ? en : vs.filter((v) => /^en/i.test(v.lang));
  // a female voice where the name says so, enhanced/natural first
  return pool.find((v) => /natural|enhanced|premium|neural/i.test(v.name) && /female|samantha|ava|allison|aria|jenny|zira|susan/i.test(v.name))
    ?? pool.find((v) => /Samantha|Ava|Allison|Aria|Jenny|Google US English|Zira/i.test(v.name)) ?? pool.find((v) => v.default) ?? pool[0];
}

export class Speaker {
  private audio = typeof Audio !== 'undefined' ? new Audio() : null;
  private run = 0;
  private urls: string[] = [];
  private settle: ((ok: boolean) => void) | null = null;
  constructor(private server: () => boolean, private onDone: () => void) {}

  get canSpeak() { return !!TTS || (this.server() && !!this.audio); }

  /** Call inside a tap or key press, before anything async. */
  prime() {
    try { if (this.audio && this.server() && this.audio.paused) { this.audio.src = SILENT; void this.audio.play().catch(() => {}); } } catch { /* ignore */ }
    try { if (TTS && !TTS.speaking) TTS.speak(new SpeechSynthesisUtterance('')); } catch { /* ignore */ }
  }

  stop() {
    this.run++;
    this.audio?.pause();
    this.settle?.(false); this.settle = null;
    TTS?.cancel();
    this.urls.forEach((u) => URL.revokeObjectURL(u)); this.urls = [];
  }

  async say(text: string) {
    this.stop();
    const run = this.run;
    const parts = sentences(text);
    const live = () => run === this.run;
    if (this.server() && this.audio) {
      const fetchPart = (s: string) => fetch(`${API_BASE}/tts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: s }) })
        .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status))))).then((b) => { const u = URL.createObjectURL(b); this.urls.push(u); return u; });
      let next: Promise<string> | null = fetchPart(parts[0]);
      for (let i = 0; i < parts.length; i++) {
        let url: string;
        try { url = await next!; } catch { if (live()) this.device(parts.slice(i).join(' '), run); return; }
        if (!live()) return;
        next = i + 1 < parts.length ? fetchPart(parts[i + 1]) : null;
        next?.catch(() => {}); // handled when awaited
        const ok = await this.play(url);
        if (!live()) return;
        if (!ok) { this.device(parts.slice(i).join(' '), run); return; }
      }
      if (live()) this.onDone();
      return;
    }
    this.device(text, run);
  }

  private play(url: string): Promise<boolean> {
    const a = this.audio!;
    return new Promise((done) => {
      const res = (ok: boolean) => { this.settle = null; done(ok); };
      this.settle = res;
      a.onended = () => res(true);
      a.onerror = () => res(false);
      a.src = url;
      a.play().catch(() => res(false));
    });
  }

  private device(text: string, run: number) {
    if (!TTS) { this.onDone(); return; }
    const u = new SpeechSynthesisUtterance(text);
    const v = deviceVoice(); if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'en-US';
    u.rate = 0.95;
    u.onend = u.onerror = () => { if (run === this.run) this.onDone(); };
    TTS.speak(u);
  }
}
