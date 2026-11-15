// Step 5 on the shared step frame: which option goes on the page, what the page holds, one Print button. The full page
// (RotationBrief) is always in the document for printing; "Preview the page" shows it.
import type { Location, RotationStrategy } from '../../types';
import { isRainFed, mmToAfac, RAIN_FED } from '../../lib';
import Icon from '../Icons';
import { acres, fieldName } from '../ui/shared';
import { Answer, KeyFacts, StepShell } from '../ui/StepShell';
import { t } from '../../i18n';
import { setPref, usePrefs } from '../a11y/prefs';
import { ax } from '../a11y/ax';

export default function BriefStep(p: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; allocation: number; exampleLimit: boolean; onPreview: () => void; onBack: () => void; onClose: () => void; onSheet?: (px: number) => void }) {
  const base = p.strategies.find((x) => x.is_baseline) ?? p.strategies[0];
  const s = p.strategies.find((x) => x.id === p.pick) ?? p.strategies.find((x) => !x.is_baseline) ?? base;
  const prefs = usePrefs();
  if (!s) return null;
  const need = (x: RotationStrategy) => (isRainFed(x) ? RAIN_FED : t('ui.brief.about_af', { n: mmToAfac(x.water.irrigation_need_mm.value).toFixed(1) }));
  return (
    <StepShell id="brief" testid="brief-step" resetKey={p.loc.id} onSheet={p.onSheet} onClose={p.onClose} onBack={p.onBack}
      field={<><b>{fieldName(p.loc)}</b> · {t('ui.n_acres', { n: acres(p.loc) })}</>}
      title={t('ui.brief.title')}
      answer={<Answer tone="good" headline={t('ui.brief.ready')} sub={s.is_baseline ? t('ui.brief.covers') : t('ui.brief.compares', { name: s.short_name.toLowerCase() })} />}
      next={{ label: t('ui.brief.print'), sub: t('ui.act.brief_s'), icon: 'print', onClick: () => window.print(), testid: 'print' }}>
      <label className="mi-switch lp-toggle simple-keep"><input type="checkbox" checked={prefs.largePrint} onChange={(e) => setPref('largePrint', e.target.checked)} data-testid="large-print" /><span className="mi-track" aria-hidden="true" />
        <span><b>{ax('largePrint')}</b><small>{ax('largePrintHint')}</small></span></label>
      <div className="opt-list" role="radiogroup" aria-label={t('ui.brief.option')}>
        {[...p.strategies].sort((a, b) => Number(b.is_baseline) - Number(a.is_baseline)).map((x) => (
          <button key={x.id} role="radio" aria-checked={x.id === s.id} className={`opt-row ${x.id === s.id ? 'on' : ''}`} onClick={() => p.setPick(x.id)} data-testid={`brief-pick-${x.id}`}>
            <span className="opt-radio" aria-hidden="true" />
            <span className="opt-body"><b>{x.short_name}{x.is_baseline ? ` (${t('ui.brief.today')})` : ''}</b><small>{need(x)}</small></span>
          </button>
        ))}
      </div>
      <h2 className="fp-h">{t('ui.brief.onpage')}</h2>
      <KeyFacts facts={[
        { label: t('ui.brief.f1'), value: t('ui.brief.f1v') },
        { label: t('ui.brief.f2'), value: t('ui.brief.f2v') },
        { label: t('ui.brief.f3'), value: t('ui.brief.f3v', { n: p.allocation.toFixed(1), ex: p.exampleLimit ? ` ${t('ui.fnow.example')}` : '' }) },
        { label: t('ui.brief.f4'), value: t('ui.brief.f4v') },
      ]} />
      <button className="btn btn-outline btn-block preview-btn" onClick={p.onPreview} data-testid="brief-preview"><Icon name="brief" />{t('ui.brief.preview')}</button>
    </StepShell>
  );
}
