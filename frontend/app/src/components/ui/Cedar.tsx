// Cedar: small field buddy that explains the numbers on screen. Rule-based, no model call.
import { useMemo, useState } from 'react';
import type { Location, Regional, RotationStrategy } from '../../types';
import { mmToAfac, ordinal } from '../../lib';
import { soilFacts } from './shared';

export type CedarCtx = {
  loc: Location;
  regional: Regional | null;
  strategies: RotationStrategy[] | null;
  allocation?: number;
  takeaway?: string | null;
};

type Msg = { who: 'cedar' | 'you'; text: string };

const HELLO = "Hey — I'm Cedar. Ask me about water, soil, or what these meters mean. Short answers only.";

function reply(q: string, ctx: CedarCtx): string {
  const t = q.toLowerCase();
  const base = ctx.strategies?.find((s) => s.is_baseline);
  const need = base ? mmToAfac(base.water.irrigation_need_mm.value) : null;
  const lim = ctx.allocation;
  const soil = soilFacts(ctx.loc.soil);
  const smVals = ctx.regional?.smap_rootzone_pct.values.filter((v): v is number => v != null) ?? [];
  const gwVals = ctx.regional?.grace_gw_pct.values.filter((v): v is number => v != null) ?? [];
  const smap = smVals.length ? smVals[smVals.length - 1] : null;
  const grace = gwVals.length ? gwVals[gwVals.length - 1] : null;

  if (/hello|hi\b|hey|who are you|your name/.test(t)) {
    return "Cedar. Think of me as the neighbour who read the water letter so you don't have to squint at every percentile.";
  }
  if (/soil|sand|silt|clay|texture|composition|holds|drain/.test(t)) {
    const bits = [soil.texture && `${soil.texture} soil`, soil.mix && `${Math.round(soil.mix.sand)}% sand, ${Math.round(soil.mix.silt)}% silt, ${Math.round(soil.mix.clay)}% clay`, soil.holds, soil.drains, soil.salt].filter(Boolean);
    return bits.length ? bits.join('. ') + (soil.rotation ? ` ${soil.rotation}` : '') : "Soil card isn't loaded yet — open Field now and I'll read it with you.";
  }
  if (/ground.?water|grace|well/.test(t)) {
    return grace == null
      ? "No groundwater reading right now. When it shows, 50 is normal for the basin — not your own well."
      : `Groundwater sits around the ${ordinal(Math.round(grace))} percentile for the basin (50 = normal). It's a wide area, not your pump.`;
  }
  if (/moist|smap|wetter|drier|wet\b|dry\b/.test(t)) {
    return smap == null
      ? "No soil-moisture reading yet. When it lands, above ~67 means wetter than usual for the date."
      : `Soil moisture is about the ${ordinal(Math.round(smap))} percentile — ${smap >= 67 ? 'wetter than usual' : smap <= 33 ? 'drier than usual' : 'about normal'} for this time of year.`;
  }
  if (/water|limit|acre.?ft|irrigation|short|fit|licence|license|alloc/.test(t)) {
    if (need == null || lim == null) return "Pick a field and I'll compare today's rotation to your water limit.";
    const gap = need - lim;
    return gap > 0.05
      ? `Today's plan wants about ${need.toFixed(1)} acre-ft/acre. Your limit is ${lim.toFixed(1)}, so you're short by ~${gap.toFixed(1)}. Compare can find a lighter mix.`
      : `Today's plan needs about ${need.toFixed(1)} acre-ft/acre against your ${lim.toFixed(1)} limit — it fits in a typical year.`;
  }
  if (/percent|meter|number|stat|mean|what does/.test(t)) {
    return "Bars and percentiles: middle is normal for that date. Acre-feet per acre is how much irrigation the rotation wants in a year. If you're short, Compare is next.";
  }
  if (/nation|reserve|first|indigenous|splatsin|neskonlith/.test(t)) {
    const fn = ctx.loc.first_nations;
    if (!fn) return "This demo field isn't on reserve. Open the Nations card on Pick for nearby reserves and Splatsin on the lower river.";
    return fn.field_on_reserve
      ? "This field is on reserve land — we'd only show that with the Nation's permission."
      : `Not on reserve. Nearest is about ${fn.nearest_km} km (${fn.nearest_nation}). Splatsin sits on the lower Salmon River. We don't speak for any Nation.`;
  }
  if (/help|what can|ask/.test(t)) {
    return "Try: “Will my water cover it?”, “What’s the soil?”, “Is it dry?”, or “Any First Nations nearby?”";
  }
  if (ctx.takeaway) return `Quick read: ${ctx.takeaway} Ask about soil, water, or moisture if you want the why.`;
  return "I only know what's on this screen. Ask about water, soil, moisture, or nearby Nations.";
}

const CHIPS = ['Will my water cover it?', 'What’s the soil?', 'Is moisture low?', 'Any Nations nearby?'];

export function CedarChat({ ctx }: { ctx: CedarCtx }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [msgs, setMsgs] = useState<Msg[]>([{ who: 'cedar', text: HELLO }]);
  const id = useMemo(() => ctx.loc.id, [ctx.loc.id]);

  const ask = (q: string) => {
    const text = q.trim();
    if (!text) return;
    setMsgs((m) => [...m, { who: 'you', text }, { who: 'cedar', text: reply(text, ctx) }]);
    setInput('');
  };

  return (
    <div className={`cedar ${open ? 'open' : ''}`} data-testid="cedar">
      {!open && (
        <button type="button" className="cedar-fab" onClick={() => setOpen(true)} title="Ask Cedar about the numbers">
          <span className="cedar-avatar" aria-hidden>C</span>
          <span>Ask Cedar</span>
        </button>
      )}
      {open && (
        <div className="cedar-panel" role="dialog" aria-label="Cedar field buddy">
          <header className="cedar-head">
            <span className="cedar-avatar" aria-hidden>C</span>
            <div>
              <b>Cedar</b>
              <small>Explains the numbers · not advice</small>
            </div>
            <button type="button" className="cedar-x" onClick={() => setOpen(false)} aria-label="Close Cedar">×</button>
          </header>
          <div className="cedar-msgs" key={id}>
            {msgs.map((m, i) => (
              <p key={i} className={`cedar-msg ${m.who}`}>{m.text}</p>
            ))}
          </div>
          <div className="cedar-chips">
            {CHIPS.map((c) => (
              <button key={c} type="button" onClick={() => ask(c)}>{c}</button>
            ))}
          </div>
          <form className="cedar-form" onSubmit={(e) => { e.preventDefault(); ask(input); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about water or soil…" aria-label="Ask Cedar" />
            <button type="submit">Ask</button>
          </form>
        </div>
      )}
    </div>
  );
}
