// "First Nations lands" list for step 1 (Pick): every reserve and tribal land, filter BC / California / All, search,
// grouped by province or state, then Nation. Nations are collapsed groups (keyboard: Tab, Enter) so 1,800 rows stay light.
import { useMemo, useState } from 'react';
import Icon from '../Icons';
import { t, locale } from '../../i18n';
import { areaText, kindLabel, regionName, regionOf, type LandFeature } from './lands';

type Filter = 'all' | 'BC' | 'CA';
export function LandsList({ lands, activeId, onPick }: { lands: LandFeature[] | null; activeId: string | null; onPick: (id: string) => void }) {
  const [q, setQ] = useState('');
  const [f, setF] = useState<Filter>('all');
  const [open, setOpen] = useState<Set<string>>(new Set());
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const counts = useMemo(() => ({ BC: lands?.filter((l) => regionOf(l.properties) === 'BC').length ?? 0, CA: lands?.filter((l) => regionOf(l.properties) === 'CA').length ?? 0 }), [lands]);
  const groups = useMemo(() => {
    const out: { region: 'BC' | 'CA'; nations: { nation: string; rows: LandFeature[] }[] }[] = [];
    for (const region of ['CA', 'BC'] as const) {
      if (f !== 'all' && f !== region) continue;
      const by = new Map<string, LandFeature[]>();
      for (const l of lands ?? []) {
        const p = l.properties;
        if (regionOf(p) !== region) continue;
        if (words.length && !words.every((w) => `${p.name} ${p.nation} ${regionName(region)} ${region} ${kindLabel(p.kind)}`.toLowerCase().includes(w))) continue;
        (by.get(p.nation) ?? by.set(p.nation, []).get(p.nation)!).push(l);
      }
      const nations = [...by].map(([nation, rows]) => ({ nation, rows: rows.sort((a, b) => a.properties.name.localeCompare(b.properties.name)) })).sort((a, b) => a.nation.localeCompare(b.nation));
      if (nations.length) out.push({ region, nations });
    }
    return out;
  }, [lands, f, q]); // eslint-disable-line react-hooks/exhaustive-deps
  const total = groups.reduce((n, g) => n + g.nations.reduce((m, x) => m + x.rows.length, 0), 0);
  const searching = words.length > 0;
  const activeNation = lands?.find((l) => l.properties.id === activeId)?.properties.nation;
  return (
    <div className="ll" data-testid="lands-list">
      <div className="pk-filter">
        <label className="pk-search"><Icon name="search" size={16} /><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('ll.ph')} aria-label={t('ll.aria')} data-testid="lands-search" /></label>
        <div className="chips" role="group" aria-label={t('ll.region')}>
          {([['all', t('ll.all'), counts.BC + counts.CA], ['BC', regionName('BC'), counts.BC], ['CA', regionName('CA'), counts.CA]] as const).map(([k, label, n]) => (
            <button key={k} className="chip" aria-pressed={f === k} onClick={() => setF(k)} data-testid={`lands-filter-${k}`}><Icon name="check" size={16} className="check" />{label} <span className="n">{n.toLocaleString(locale)}</span></button>
          ))}
        </div>
      </div>
      {!lands && <p className="loading-note">{t('ll.loading')}</p>}
      {lands && <p className="ll-count" role="status" aria-live="polite">{t(`ll.cnt${total === 1 ? '1' : 'n'}${searching ? 'm' : ''}`, { n: total.toLocaleString(locale) })}</p>}
      {groups.map((g) => (
        <section key={g.region} aria-label={regionName(g.region)}>
          <h2 className="pk-group">{regionName(g.region)}</h2>
          <ul className="ll-nations">
            {g.nations.map((n) => {
              const key = g.region + n.nation, isOpen = open.has(key) || n.nation === activeNation || (searching && n.rows.length <= 12);
              return (
                <li key={key}>
                  <details open={isOpen} onToggle={(e) => { const o = (e.currentTarget as HTMLDetailsElement).open; if (o !== open.has(key)) setOpen((s) => { const t = new Set(s); if (o) t.add(key); else t.delete(key); return t; }); }}>
                    <summary><b>{n.nation}</b><span>{t(n.rows.length === 1 ? 'll.cnt1' : 'll.cntn', { n: n.rows.length })}</span><Icon name="chevdown" size={18} /></summary>
                    {isOpen && (
                      <ul className="ll-rows">
                        {n.rows.map((l) => {
                          const p = l.properties;
                          return (
                            <li key={p.id}>
                              <button className={`ll-row ${activeId === p.id ? 'on' : ''}`} aria-current={activeId === p.id ? 'true' : undefined} onClick={() => onPick(p.id)} data-testid={`land-row-${p.id}`}>
                                <i className={`ll-dot ${p.kind}`} aria-hidden="true" />
                                <span className="ll-main"><b>{p.name}</b><small>{p.nation} · {kindLabel(p.kind)}</small></span>
                                <em>{areaText(p.area_ha).split(' (')[0]}</em>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </details>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
      {lands && !total && <p className="loading-note">{t('ll.none')} <button className="btn btn-outline btn-sm" onClick={() => { setQ(''); setF('all'); }}>{t('ll.showAll')}</button></p>}
      <p className="ll-fine">{t('ll.fine')}</p>
    </div>
  );
}
