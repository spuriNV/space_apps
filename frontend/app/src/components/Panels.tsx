import type { BCInfo, Dataset, Location } from '../types';
import Icon from './Icons';
import { t, locale } from '../i18n';

// ---------- "Why not BC yet" ----------
export function BCCard({ bc, onClose, floating }: { bc: BCInfo; onClose?: () => void; floating?: boolean }) {
  return (
    <div className={`bc-card ${floating ? 'glass floating' : ''}`} data-testid="bc-card">
      <div className="bc-head">
        <span className="chip warn"><Icon name="info" size={13} />{t('pan.oos')}</span>
        {onClose && <button className="icon-btn" onClick={onClose} aria-label={t('common.close')}><Icon name="close" size={16} /></button>}
      </div>
      <h3>{bc.title}</h3>
      <p>{bc.intro}</p>
      <ul>
        {bc.lines.map((l) => <li key={l.label}><b>{l.label}</b><span>{l.text}</span></li>)}
      </ul>
      <p className="muted">{bc.limit}</p>
      <span className="bc-next"><Icon name="right" size={14} />{bc.next_step.label} <small>({bc.next_step.ref})</small></span>
    </div>
  );
}

// ---------- Layers drawer ----------
export function LayersDrawer(p: { datasets: Dataset[]; on: Record<string, boolean>; toggle: (id: string) => void; loc: Location | null; reserves?: boolean; landsCount?: number | null; onClose: () => void }) {
  const fieldKm2 = p.loc ? p.loc.area_ha.value / 100 : 0.6;
  const group = (g: 'field' | 'regional', title: string, sub: string) => (
    <div className="lg">
      <h3>{title}<small>{sub}</small></h3>
      {p.datasets.filter((d) => d.group === g).map((d) => {
        const px = (d.footprint_m / 1000) ** 2;
        const ratio = px >= fieldKm2 ? t('pan.ratio1', { n: Math.round(px / fieldKm2).toLocaleString(locale) }) : t('pan.ratio2', { n: Math.round(fieldKm2 / px).toLocaleString(locale) });
        return (
          <label key={d.id} className={`layer ${p.on[d.id] ? 'on' : ''}`}>
            <input type="checkbox" checked={!!p.on[d.id]} onChange={() => p.toggle(d.id)} data-testid={`layer-${d.id}`} />
            <span className="sw" style={p.on[d.id] ? { background: d.color } : undefined} />
            <span className="layer-body">
              <span className="layer-top"><b>{d.name}</b><span className="px" style={{ borderColor: d.color, color: d.color }}>{d.native_scale}</span></span>
              <span className="layer-sees">{d.sees}</span>
              <span className="layer-meta">{t('pan.meta', { ratio, cad: d.cadence, since: d.since })}{d.in_stack ? t('pan.in3d', { v: d.in_stack }) : ''}</span>
              {d.caveat && <span className="layer-meta caveat">{d.caveat}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
  return (
    <aside className="drawer glass" data-testid="layers-drawer">
      <header className="panel-head"><h2>{t('pan.layers')} <small>{t('pan.earth')}</small></h2><button className="icon-btn" onClick={p.onClose} aria-label={t('common.close')} title={t('common.close')}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll">
        <div className="lg" data-testid="layer-group-lands">
          <h3>{t('pan.fn')}<small>{t('pan.fnSub')}</small></h3>
          <label className={`layer ${p.on.lands ? 'on' : ''}`}>
            <input type="checkbox" checked={!!p.on.lands} onChange={() => p.toggle('lands')} data-testid="layer-lands" />
            <span className="sw sw-reserve" />
            <span className="layer-body">
              <span className="layer-top"><b>{t('pan.fnLands')}</b></span>
              <span className="layer-sees">{t('pan.fnSees', { n: p.landsCount ? ` (${p.landsCount.toLocaleString(locale)})` : '' })}</span>
              <span className="layer-meta">{t('pan.fnMeta')}</span>
            </span>
          </label>
        </div>
        {p.reserves && !p.on.lands && (
          <div className="lg" data-testid="layer-group-context">
            <h3>{t('pan.ctx')}<small>{t('pan.ctxSub')}</small></h3>
            <label className={`layer ${p.on.reserves ? 'on' : ''}`}>
              <input type="checkbox" checked={!!p.on.reserves} onChange={() => p.toggle('reserves')} data-testid="layer-reserves" />
              <span className="sw sw-reserve" />
              <span className="layer-body">
                <span className="layer-top"><b>{t('pan.resB')}</b></span>
                <span className="layer-sees">{t('pan.resSees')}</span>
                <span className="layer-meta">{t('pan.resMeta')}</span>
              </span>
            </label>
          </div>
        )}
        {group('field', t('pan.inside'), t('pan.insideSub'))}
        {group('regional', t('pan.basin'), t('pan.basinSub'))}
        <div className="scale-ruler">
          <h3>{t('pan.pixel')} <small>{t('pan.log')}</small></h3>
          {p.datasets.map((d) => (
            <div key={d.id} className="ruler-row"><span>{d.name}</span><i style={{ width: `${8 + Math.log10(d.footprint_m / 30) * 30}%`, background: d.color }} /><em>{d.native_scale}</em></div>
          ))}
          <div className="ruler-row field"><span>{t('pan.yourField')}</span><i style={{ width: `${8 + Math.log10(Math.sqrt(fieldKm2) * 1000 / 30) * 30}%` }} /><em>≈ {(Math.sqrt(fieldKm2)).toFixed(1)} km</em></div>
        </div>
        <p className="footnote">{t('pan.foot')}</p>
      </div>
    </aside>
  );
}

