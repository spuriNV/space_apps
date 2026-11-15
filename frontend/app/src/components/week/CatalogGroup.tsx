// "Farm catalog" group at the end of the pick list: a collapsible list of the catalog farms with crop-group filter chips.
// The same chips filter the map pins (state lives in App). Clicking a farm opens the point panel for its pt_ id.
import { useMemo, useRef, useState } from 'react';
import Icon from '../Icons';
import { t } from '../../i18n';
import { groupColor, groupLetter, landNote, type Catalog, type CatalogItem } from './catalog';
import './catalog.css';

const PAGE = 30;
export function CatalogGroup({ catalog, group, setGroup, onPick }: { catalog: Catalog; group: string | null; setGroup: (g: string | null) => void; onPick: (it: CatalogItem) => void }) {
  const [open, setOpen] = useState(false);
  const [n, setN] = useState(PAGE);
  const [country, setCountry] = useState('');
  const [state, setState] = useState('');
  const ref = useRef<HTMLElement>(null);
  const toggle = () => { const o = !open; setOpen(o); if (o) setTimeout(() => ref.current?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }), 340); };
  const groups = Object.entries(catalog.crop_groups).sort((a, b) => b[1].count - a[1].count);
  const countries = useMemo(() => [...new Set(catalog.items.map((i) => i.country).filter(Boolean) as string[])].sort(), [catalog.items]);
  const states = useMemo(() => [...new Set(catalog.items.filter((i) => !country || i.country === country).map((i) => i.state).filter(Boolean) as string[])].sort(), [catalog.items, country]);
  const rows = useMemo(() => catalog.items.filter((i) => (!group || i.crop_group === group) && (!country || i.country === country) && (!state || i.state === state))
    .sort((a, b) => (a.state ?? '').localeCompare(b.state ?? '') || a.name.localeCompare(b.name)), [catalog.items, group, country, state]);
  const CN: Record<string, string> = { US: 'United States', CA: 'Canada' };
  return (
    <section className="cg" ref={ref} data-testid="farm-catalog">
      <button className={`more-detail cg-toggle ${open ? 'on' : ''}`} onClick={toggle} aria-expanded={open}>
        <span><b>{t('week.catTitle')}</b><small>{t('week.catSub', { n: catalog.total })}</small></span><Icon name="chevdown" size={20} />
      </button>
      <div className={`cg-more ${open ? 'on' : ''}`}>
        <div className="cg-in">
          <div className="cg-sel">
            <label>Country<select value={country} onChange={(e) => { setCountry(e.target.value); setState(''); setN(PAGE); }} data-testid="cat-country">
              <option value="">All countries</option>{countries.map((c) => <option key={c} value={c}>{CN[c] ?? c}</option>)}</select></label>
            <label>{country === 'CA' ? 'Province' : country === 'US' ? 'State' : 'State or province'}<select value={state} onChange={(e) => { setState(e.target.value); setN(PAGE); }} data-testid="cat-state">
              <option value="">All</option>{states.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
          </div>
          <p className="nt-fine cg-count" role="status" aria-live="polite">{rows.length} {rows.length === 1 ? 'farm' : 'farms'}</p>
          <div className="chips cg-chips" role="group" aria-label={t('week.cropGroup')}>
            {groups.map(([g, v]) => (
              <button key={g} className="chip" aria-pressed={group === g} onClick={() => { setGroup(group === g ? null : g); setN(PAGE); }}>
                <Icon name="check" size={16} /><i className="cg-dot" style={{ background: groupColor(g) }} aria-hidden="true">{groupLetter(g)}</i>{v.label} <span className="n">{v.count}</span>
              </button>
            ))}
          </div>
          <ul className="pk-list cg-list">
            {open && rows.slice(0, n).map((it, k) => (
              <li key={it.id}>
                {it.state && (k === 0 || rows[k - 1].state !== it.state) && <h4 className="cg-state">{it.state}</h4>}
                <button className="pk-row cg-row" onClick={() => onPick(it)} data-testid={`cat-${it.id}`}>
                  <i className="cg-dot" style={{ background: groupColor(it.crop_group) }} aria-hidden="true">{groupLetter(it.crop_group)}</i>
                  <span className="pk-body"><b>{it.name}</b>
                    <span className="pk-facts">{it.crop_group_label}{it.acres ? ` · ${t('week.acresN', { n: Math.round(it.acres) })}` : ''} · {it.area}{it.state ? `, ${it.state}` : ''}</span>
                    {landNote(it.land_status) && <span className="pk-note">{landNote(it.land_status)}</span>}</span>
                </button>
              </li>
            ))}
          </ul>
          {rows.length > n && <button className="btn btn-outline btn-sm cg-more-btn" onClick={() => setN(n + PAGE)}>{t('week.showMore', { n: Math.min(PAGE, rows.length - n) })}</button>}
          <p className="nt-fine cg-note">{t('week.catNote')}</p>
        </div>
      </div>
    </section>
  );
}
