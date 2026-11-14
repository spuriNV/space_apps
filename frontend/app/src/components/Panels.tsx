import type { BCInfo, Dataset, Location } from '../types';
import Icon from './Icons';

// ---------- "Why not BC yet" ----------
export function BCCard({ bc, onClose, floating }: { bc: BCInfo; onClose?: () => void; floating?: boolean }) {
  return (
    <div className={`bc-card ${floating ? 'glass floating' : ''}`} data-testid="bc-card">
      <div className="bc-head">
        <span className="chip warn"><Icon name="info" size={13} />Out of scope for now</span>
        {onClose && <button className="icon-btn" onClick={onClose}><Icon name="close" size={16} /></button>}
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
export function LayersDrawer(p: { datasets: Dataset[]; on: Record<string, boolean>; toggle: (id: string) => void; loc: Location | null; onClose: () => void }) {
  const fieldKm2 = p.loc ? p.loc.area_ha.value / 100 : 0.6;
  const group = (g: 'field' | 'regional', title: string, sub: string) => (
    <div className="lg">
      <h3>{title}<small>{sub}</small></h3>
      {p.datasets.filter((d) => d.group === g).map((d) => {
        const px = (d.footprint_m / 1000) ** 2;
        const ratio = px >= fieldKm2 ? `1 pixel ≈ ${Math.round(px / fieldKm2).toLocaleString()} fields this size` : `≈ ${Math.round(fieldKm2 / px).toLocaleString()} pixels inside the field`;
        return (
          <label key={d.id} className={`layer ${p.on[d.id] ? 'on' : ''}`}>
            <input type="checkbox" checked={!!p.on[d.id]} onChange={() => p.toggle(d.id)} data-testid={`layer-${d.id}`} />
            <span className="sw" style={p.on[d.id] ? { background: d.color } : undefined} />
            <span className="layer-body">
              <span className="layer-top"><b>{d.name}</b><span className="px" style={{ borderColor: d.color, color: d.color }}>{d.native_scale}</span></span>
              <span className="layer-sees">{d.sees}</span>
              <span className="layer-meta">{ratio} · {d.cadence} · since {d.since}{d.in_stack ? ` · in 3D stack: ${d.in_stack}` : ''}</span>
              {d.caveat && <span className="layer-meta caveat">{d.caveat}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
  return (
    <aside className="drawer glass" data-testid="layers-drawer">
      <header className="panel-head"><h2>Layers <small>NASA Earth data</small></h2><button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll">
        {group('field', 'Sees inside your field', 'pixel smaller than the field')}
        {group('regional', 'Sees your district or basin', 'one pixel covers many fields')}
        <div className="scale-ruler">
          <h3>Pixel size, to scale <small>log</small></h3>
          {p.datasets.map((d) => (
            <div key={d.id} className="ruler-row"><span>{d.name}</span><i style={{ width: `${8 + Math.log10(d.footprint_m / 30) * 30}%`, background: d.color }} /><em>{d.native_scale}</em></div>
          ))}
          <div className="ruler-row field"><span>Your field</span><i style={{ width: `${8 + Math.log10(Math.sqrt(fieldKm2) * 1000 / 30) * 30}%` }} /><em>≈ {(Math.sqrt(fieldKm2)).toFixed(1)} km</em></div>
        </div>
        <p className="footnote">Coarse satellites describe weeks and years across the valley. They cannot tell one field from its neighbour.</p>
      </div>
    </aside>
  );
}

