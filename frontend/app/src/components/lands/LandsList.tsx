// "First Nations lands" list for step 1 (Pick): every reserve and tribal land, filter BC / California / All, search,
// grouped by province or state, then Nation. Nations are collapsed groups (keyboard: Tab, Enter) so 1,800 rows stay light.
import { useMemo, useState } from 'react';
import Icon from '../Icons';
import { areaText, kindLabel, regionName, regionOf, type LandFeature } from './lands';

type Filter = 'all' | 'US' | 'CAN';
const NATION_PAGE = 120;
export function LandsList({ lands, activeId, onPick }: { lands: LandFeature[] | null; activeId: string | null; onPick: (id: string) => void }) {
  const [q, setQ] = useState('');
  const [f, setF] = useState<Filter>('all');
  const [reg, setReg] = useState('');
  const [more, setMore] = useState(1);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const counts = useMemo(() => ({ US: lands?.filter((l) => l.properties.country === 'US').length ?? 0, CAN: lands?.filter((l) => l.properties.country === 'CAN').length ?? 0 }), [lands]);
  const regions = useMemo(() => {
    const m = new Map<string, number>();
    for (const l of lands ?? []) if (f === 'all' || l.properties.country === f) m.set(regionOf(l.properties), (m.get(regionOf(l.properties)) ?? 0) + 1);
    return [...m].sort((a, b) => regionName(a[0]).localeCompare(regionName(b[0])));
  }, [lands, f]);
  const groups = useMemo(() => {
    const out: { region: string; nations: { nation: string; rows: LandFeature[] }[] }[] = [];
    const by = new Map<string, Map<string, LandFeature[]>>();
    for (const l of lands ?? []) {
      const p = l.properties, r = regionOf(p);
      if ((f !== 'all' && p.country !== f) || (reg && r !== reg)) continue;
      if (words.length && !words.every((w) => `${p.name} ${p.nation} ${regionName(r)} ${r} ${p.country === 'CAN' ? 'canada' : 'united states usa'} ${kindLabel(p.kind)}`.toLowerCase().includes(w))) continue;
      const m = by.get(r) ?? by.set(r, new Map()).get(r)!;
      (m.get(p.nation) ?? m.set(p.nation, []).get(p.nation)!).push(l);
    }
    for (const r of [...by.keys()].sort((a, b) => regionName(a).localeCompare(regionName(b)))) {
      const nations = [...by.get(r)!].map(([nation, rows]) => ({ nation, rows: rows.sort((a, b) => a.properties.name.localeCompare(b.properties.name)) })).sort((a, b) => a.nation.localeCompare(b.nation));
      out.push({ region: r, nations });
    }
    return out;
  }, [lands, f, reg, q]); // eslint-disable-line react-hooks/exhaustive-deps
  let budget = NATION_PAGE * more;
  const shown = groups.map((g) => { const ns = g.nations.slice(0, Math.max(0, budget)); budget -= g.nations.length; return { ...g, nations: ns }; }).filter((g) => g.nations.length);
  const hidden = groups.reduce((n, g) => n + g.nations.length, 0) - shown.reduce((n, g) => n + g.nations.length, 0);
  const total = groups.reduce((n, g) => n + g.nations.reduce((m, x) => m + x.rows.length, 0), 0);
  const searching = words.length > 0;
  const activeNation = lands?.find((l) => l.properties.id === activeId)?.properties.nation;
  return (
    <div className="ll" data-testid="lands-list">
      <div className="pk-filter">
        <label className="pk-search"><Icon name="search" size={16} /><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by reserve, tribe, Nation or state" aria-label="Search First Nations lands" data-testid="lands-search" /></label>
        <div className="chips" role="group" aria-label="Country">
          {([['all', 'All', counts.US + counts.CAN], ['US', 'United States', counts.US], ['CAN', 'Canada', counts.CAN]] as const).map(([k, label, n]) => (
            <button key={k} className="chip" aria-pressed={f === k} onClick={() => { setF(k); setReg(''); setMore(1); }} data-testid={`lands-filter-${k}`}><Icon name="check" size={16} className="check" />{label} <span className="n">{n.toLocaleString('en-US')}</span></button>
          ))}
        </div>
        <label className="ll-region"><span>{f === 'CAN' ? 'Province or territory' : f === 'US' ? 'State' : 'State or province'}</span>
          <select value={reg} onChange={(e) => { setReg(e.target.value); setMore(1); }} aria-label="State or province" data-testid="lands-region">
            <option value="">All ({regions.length})</option>
            {regions.map(([r, n]) => <option key={r} value={r}>{regionName(r)} ({n.toLocaleString('en-US')})</option>)}
          </select>
        </label>
      </div>
      {!lands && <p className="loading-note">Loading the lands…</p>}
      {lands && <p className="ll-count" role="status" aria-live="polite">{total.toLocaleString('en-US')} {total === 1 ? 'land' : 'lands'}{searching ? ' match' : ''}</p>}
      {shown.map((g) => (
        <section key={g.region} aria-label={regionName(g.region)}>
          <h2 className="pk-group">{regionName(g.region)}</h2>
          <ul className="ll-nations">
            {g.nations.map((n) => {
              const key = g.region + '|' + n.nation, isOpen = open.has(key) || n.nation === activeNation || (searching && n.rows.length <= 12);
              return (
                <li key={key}>
                  <details open={isOpen} onToggle={(e) => { const o = (e.currentTarget as HTMLDetailsElement).open; if (o !== open.has(key)) setOpen((s) => { const t = new Set(s); if (o) t.add(key); else t.delete(key); return t; }); }}>
                    <summary><b>{n.nation}</b><span>{n.rows.length} {n.rows.length === 1 ? 'land' : 'lands'}</span><Icon name="chevdown" size={18} /></summary>
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
      {hidden > 0 && <p className="loading-note"><button className="btn btn-outline btn-sm" onClick={() => setMore(more + 1)} data-testid="lands-more">Show {Math.min(hidden, NATION_PAGE)} more Nations</button> {hidden.toLocaleString('en-US')} not shown. Search or pick a state to narrow.</p>}
      {lands && !total && <p className="loading-note">No land matches. <button className="btn btn-outline btn-sm" onClick={() => { setQ(''); setF('all'); setReg(''); }}>Show all</button></p>}
      <p className="ll-fine">Reserve and trust boundaries are legal or statistical lines, not traditional territory.</p>
    </div>
  );
}
