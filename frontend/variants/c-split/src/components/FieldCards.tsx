import { getBcCard, getCells, getFieldYear, getLocations, haToAc } from '../api';
import { MEASURES, colorFor } from '../measures';
import type { Location } from '../types';
import { Icon, fmt } from './Bits';

export function FieldThumb({ loc }: { loc: Location }) {
  const cells = getCells(loc.id).features;
  const { cols, rows } = loc.grid;
  return (
    <svg className="thumb-svg" viewBox={`-2 -2 ${cols + 4} ${rows + 4}`} preserveAspectRatio="xMidYMid meet" aria-hidden>
      {cells.map((c) => (
        <rect key={c.properties.id} x={c.properties.col} y={rows - 1 - c.properties.row} width={1.03} height={1.03} fill={colorFor(MEASURES.ndvi, c.properties.ndvi)} />
      ))}
    </svg>
  );
}

const cropTone = (c: string) => (c.startsWith('Fallow') ? 'b' : c.includes('Rice') ? 'rice' : c.includes('Alfalfa') ? 'c' : 'p');

export default function FieldCards({ visible, hoverId, onHover, onOpen }: { visible: string[]; hoverId: string | null; onHover: (id: string | null) => void; onOpen: (id: string) => void }) {
  const locs = getLocations();
  const bc = getBcCard();
  const inView = locs.filter((l) => visible.includes(l.id));
  const sorted = [...inView, ...locs.filter((l) => !visible.includes(l.id))];
  return (
    <div className="pane">
      <div className="pane-head">
        <h1>{inView.length === 0 ? 'No example fields in this map area' : `${inView.length} example field${inView.length > 1 ? 's' : ''} in this map area`}</h1>
        <p>California · pick a field to compare its crop rotations with NASA Earth data. Move the map and this list follows.</p>
      </div>
      <div className="cards">
        {sorted.map((l) => {
          const out = !visible.includes(l.id);
          const hist = Object.entries(l.crop_history);
          return (
            <article
              key={l.id} className={`fcard${hoverId === l.id ? ' hover' : ''}${out ? ' out' : ''}`} data-loc={l.id} tabIndex={0}
              onMouseEnter={() => onHover(l.id)} onMouseLeave={() => onHover(null)} onClick={() => onOpen(l.id)}
              onKeyDown={(e) => e.key === 'Enter' && onOpen(l.id)}
            >
              <div className="fthumb">
                <FieldThumb loc={l} />
                <span className="fthumb-cap">30 m cover, Jul 2025</span>
                <span className="fthumb-badge">Example field</span>
              </div>
              <div className="fbody">
                <div className="frow1">
                  <h2>{l.short_name}</h2>
                  <span className="badge rich" title="OpenET, SSURGO soils, CIMIS stations and crop labels are all available here">Ground data: rich</span>
                </div>
                <div className="fsub">{l.region_label}{out && <em> · outside map view</em>}</div>
                <div className="ffacts">
                  <span><b>{fmt(l.area_ha.value, 0)} ha</b> ({fmt(haToAc(l.area_ha.value), 0)} acres)</span>
                  <span>{l.current_crop}</span>
                  <span>{l.water.source === 'surface' ? 'Surface water' : 'Groundwater'} · {l.water.sgma_subbasin} Subbasin</span>
                </div>
                <div className="fhist" title="Crop each year from the USDA Cropland Data Layer">
                  <div className="fhist-cells">
                    {hist.map(([y, c]) => <i key={y} className={`hist-${cropTone(c)}`} title={`${y}: ${c}`} />)}
                  </div>
                  <span>Crop history 2016–2025 · usually bare {l.headline.bare_window}</span>
                </div>
                <div className="ffoot">
                  <div className="fevents">
                    {l.events.slice(0, 2).map((e) => <span key={e.date} className={`evchip ev-${e.type}`}>{e.date.slice(0, 4)} {e.type === 'drought_fallow' ? 'fallow' : e.type === 'atmospheric_river' ? 'storms' : e.type === 'flood' ? 'flood' : e.type === 'sgma_probation' ? 'probation' : 'drought'}</span>)}
                    <span className="evchip plain">detectors agree {getFieldYear(l.id).detector_agreement_pct}%</span>
                  </div>
                  <span className="fcta">Compare rotations<Icon name="arrow" size={15} /></span>
                </div>
              </div>
            </article>
          );
        })}
        <article className="fcard bc" data-loc="bc">
          <div className="fthumb bc-thumb"><Icon name="info" size={26} /><span>British Columbia</span></div>
          <div className="fbody">
            <div className="frow1"><h2>{bc.title}</h2><span className="badge muted">Out of scope</span></div>
            <ul className="bclines">{bc.lines.map((t) => <li key={t}>{t}</li>)}</ul>
            <div className="bcnext">{bc.next_step}</div>
          </div>
        </article>
      </div>
      <p className="pane-foot">Example fields are typical, not measured farms. Every alternative needs review by the grower and an adviser before anything is seeded.</p>
    </div>
  );
}
