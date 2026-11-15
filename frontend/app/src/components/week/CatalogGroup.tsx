// "Farm catalog" group at the end of the pick list: a collapsible list of the catalog farms with crop-group filter chips.
// The same chips filter the map pins (state lives in App). Clicking a farm opens the point panel for its pt_ id.
import { useRef, useState } from 'react';
import Icon from '../Icons';
import { groupColor, landNote, type Catalog, type CatalogItem } from './catalog';
import './catalog.css';

const PAGE = 30;
export function CatalogGroup({ catalog, group, setGroup, onPick }: { catalog: Catalog; group: string | null; setGroup: (g: string | null) => void; onPick: (it: CatalogItem) => void }) {
  const [open, setOpen] = useState(false);
  const [n, setN] = useState(PAGE);
  const ref = useRef<HTMLElement>(null);
  const toggle = () => { const o = !open; setOpen(o); if (o) setTimeout(() => ref.current?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }), 340); };
  const groups = Object.entries(catalog.crop_groups).sort((a, b) => b[1].count - a[1].count);
  const rows = catalog.items.filter((i) => !group || i.crop_group === group);
  return (
    <section className="cg" ref={ref} data-testid="farm-catalog">
      <button className={`more-detail cg-toggle ${open ? 'on' : ''}`} onClick={toggle} aria-expanded={open}>
        <span><b>Farm catalog</b><small>{catalog.total} more farms across California and BC, by crop</small></span><Icon name="chevdown" size={20} />
      </button>
      <div className={`cg-more ${open ? 'on' : ''}`}>
        <div className="cg-in">
          <div className="chips cg-chips" role="group" aria-label="Crop group">
            {groups.map(([g, v]) => (
              <button key={g} className="chip" aria-pressed={group === g} onClick={() => { setGroup(group === g ? null : g); setN(PAGE); }}>
                <Icon name="check" size={16} /><i className="cg-dot" style={{ background: groupColor(g) }} />{v.label} <span className="n">{v.count}</span>
              </button>
            ))}
          </div>
          <ul className="pk-list cg-list">
            {open && rows.slice(0, n).map((it) => (
              <li key={it.id}>
                <button className="pk-row cg-row" onClick={() => onPick(it)} data-testid={`cat-${it.id}`}>
                  <i className="cg-dot" style={{ background: groupColor(it.crop_group) }} />
                  <span className="pk-body"><b>{it.name}</b>
                    <span className="pk-facts">{it.crop_group_label}{it.acres ? ` · ${Math.round(it.acres)} acres` : ''} · {it.area}</span>
                    {landNote(it.land_status) && <span className="pk-note">{landNote(it.land_status)}</span>}</span>
                </button>
              </li>
            ))}
          </ul>
          {rows.length > n && <button className="btn btn-outline btn-sm cg-more-btn" onClick={() => setN(n + PAGE)}>Show {Math.min(PAGE, rows.length - n)} more</button>}
          <p className="nt-fine cg-note">Each farm is a point from the public crop map; open it for live numbers.</p>
        </div>
      </div>
    </section>
  );
}
