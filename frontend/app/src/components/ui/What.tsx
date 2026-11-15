// Plain-language "What's this?" explanations, opened in place next to the word they explain.
import { useState } from 'react';
import { t } from '../../i18n';

export const GLOSSARY = {
  et: { term: t('ui.gl.et.term'), text: t('ui.gl.et.text') },
  greenness: { term: t('ui.gl.greenness.term'), text: t('ui.gl.greenness.text') },
  soilAnomaly: { term: t('ui.gl.soilAnomaly.term'), text: t('ui.gl.soilAnomaly.text') },
  frost: { term: t('ui.gl.frost.term'), text: t('ui.gl.frost.text') },
  waterBalance: { term: t('ui.gl.waterBalance.term'), text: t('ui.gl.waterBalance.text') },
  bare: { term: t('ui.gl.bare.term'), text: t('ui.gl.bare.text') },
} as const;
export type GlossKey = keyof typeof GLOSSARY | 'opera' | 'stress' | 'ruleMl' | 'heat';
const EXTRA: Record<string, { term: string; text: string }> = {
  opera: { term: t('ui.gl.opera.term'), text: t('ui.gl.opera.text') },
  stress: { term: t('ui.gl.stress.term'), text: t('ui.gl.stress.text') },
  ruleMl: { term: t('ui.gl.ruleMl.term'), text: t('ui.gl.ruleMl.text') },
  heat: { term: t('ui.gl.heat.term'), text: t('ui.gl.heat.text') },
};
/** Texts from GET /api/glossary replace the built-in ones when the API serves real content. */
const API_KEY: Record<string, string> = { et: 'et', greenness: 'ndvi', soilAnomaly: 'soil_moisture_pct', frost: 'frost', waterBalance: 'water_balance', bare: 'cover_classes', opera: 'dswx', ruleMl: 'rule_vs_ml', heat: 'heat_days' };
let fromApi: Record<string, { term: string; short: string }> = {};
export const setGlossary = (g: Record<string, { term: string; short: string }>) => { fromApi = g; };

/** Small "What's this?" link that opens a plain explanation underneath. */
export function What({ k }: { k: GlossKey }) {
  const [open, setOpen] = useState(false);
  const a = fromApi[API_KEY[k] ?? k];
  const g = a ? { term: a.term, text: a.short } : (GLOSSARY as Record<string, { term: string; text: string }>)[k] ?? EXTRA[k];
  return (
    <span className="what">
      <button className="what-btn" onClick={() => setOpen(!open)} aria-expanded={open} title={g.term}>{open ? t('ui.what.close') : t('ui.what.btn')}</button>
      {open && <span className="what-text" role="note"><b>{g.term}.</b> {g.text}</span>}
    </span>
  );
}
