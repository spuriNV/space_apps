// Step 5 on the shared step frame: which option goes on the page, what the page holds, one Print button. The full page
// (RotationBrief) is always in the document for printing; "Preview the page" shows it.
import type { Location, RotationStrategy } from '../../types';
import { isRainFed, mmToAfac, RAIN_FED } from '../../lib';
import Icon from '../Icons';
import { acres, fieldName } from '../ui/shared';
import { Answer, KeyFacts, StepShell } from '../ui/StepShell';
import { setPref, usePrefs } from '../a11y/prefs';
import { ax } from '../a11y/ax';

export default function BriefStep(p: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; allocation: number; exampleLimit: boolean; onPreview: () => void; onBack: () => void; onClose: () => void; onSheet?: (px: number) => void }) {
  const base = p.strategies.find((x) => x.is_baseline) ?? p.strategies[0];
  const s = p.strategies.find((x) => x.id === p.pick) ?? p.strategies.find((x) => !x.is_baseline) ?? base;
  const prefs = usePrefs();
  if (!s) return null;
  const need = (x: RotationStrategy) => (isRainFed(x) ? RAIN_FED : `about ${mmToAfac(x.water.irrigation_need_mm.value).toFixed(1)} acre-ft per acre`);
  return (
    <StepShell id="brief" testid="brief-step" resetKey={p.loc.id} onSheet={p.onSheet} onClose={p.onClose} onBack={p.onBack}
      field={<><b>{fieldName(p.loc)}</b> · {acres(p.loc)} acres</>}
      title="Take a one-page summary to your adviser"
      answer={<Answer tone="good" headline="Your page is ready to print." sub={s.is_baseline ? 'It covers what you grow today.' : `It compares ${s.short_name.toLowerCase()} with what you grow today.`} />}
      next={{ label: 'Print or save as PDF', sub: 'One page, Letter size', icon: 'print', onClick: () => window.print(), testid: 'print' }}>
      <label className="mi-switch lp-toggle simple-keep"><input type="checkbox" checked={prefs.largePrint} onChange={(e) => setPref('largePrint', e.target.checked)} data-testid="large-print" /><span className="mi-track" aria-hidden="true" />
        <span><b>{ax('largePrint')}</b><small>{ax('largePrintHint')}</small></span></label>
      <div className="opt-list" role="radiogroup" aria-label="Option on the page">
        {[...p.strategies].sort((a, b) => Number(b.is_baseline) - Number(a.is_baseline)).map((x) => (
          <button key={x.id} role="radio" aria-checked={x.id === s.id} className={`opt-row ${x.id === s.id ? 'on' : ''}`} onClick={() => p.setPick(x.id)} data-testid={`brief-pick-${x.id}`}>
            <span className="opt-radio" aria-hidden="true" />
            <span className="opt-body"><b>{x.short_name}{x.is_baseline ? ' (today)' : ''}</b><small>{need(x)}</small></span>
          </button>
        ))}
      </div>
      <h2 className="fp-h">On the page</h2>
      <KeyFacts facts={[
        { label: 'Your field', value: 'Soil, water source, last three crops' },
        { label: 'This season', value: 'Rain so far and the winter outlook' },
        { label: 'The option', value: `Water need against your limit of ${p.allocation.toFixed(1)}${p.exampleLimit ? ' (example)' : ''}, what you gain and give up` },
        { label: 'To check', value: 'A checklist for you and your adviser' },
      ]} />
      <button className="btn btn-outline btn-block preview-btn" onClick={p.onPreview} data-testid="brief-preview"><Icon name="brief" />Preview the page</button>
    </StepShell>
  );
}
