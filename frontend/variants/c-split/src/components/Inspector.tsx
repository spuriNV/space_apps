import { getCells, mmToIn } from '../api';
import { MEASURES, gradientCss, type MeasureKey } from '../measures';
import type { CellProps, Location } from '../types';
import { Icon, fmt } from './Bits';

export default function Inspector({ loc, measure, onMeasure, cell, onExit }: { loc: Location; measure: MeasureKey; onMeasure: (m: MeasureKey) => void; cell: CellProps | null; onExit: () => void }) {
  const m = MEASURES[measure];
  const grid = getCells(loc.id);
  const n = grid.features.length;
  const fieldPx = Math.max(5, Math.round((Math.sqrt(loc.area_ha.value * 1e4) / 9000) * 74));
  return (
    <div className="inspector" data-testid="inspector">
      <div className="insp-col insp-layers">
        <div className="insp-title"><Icon name="cube" size={16} /><b>Field block</b><span>{n} cells · 30 m</span></div>
        <div className="layerpick" role="group" aria-label="Layer">
          {(Object.keys(MEASURES) as MeasureKey[]).map((k) => (
            <button key={k} aria-pressed={measure === k} onClick={() => onMeasure(k)} data-measure={k}>
              <i style={{ background: gradientCss(MEASURES[k]) }} />{MEASURES[k].label}
            </button>
          ))}
        </div>
        <div className="insp-note">The valley is flat: block height shows the data value, not the terrain.</div>
      </div>
      <div className="insp-col insp-legend">
        <label>{m.long}</label>
        <div className="grad" style={{ background: gradientCss(m) }} />
        <div className="grad-ends"><span>{m.fmt(m.domain[0])} {m.lowLabel}</span><span>{m.highLabel} {m.fmt(m.domain[1])} {m.unit}</span></div>
        <div className="insp-src">{m.source} · scene {grid.scene_date} · taller = higher</div>
      </div>
      <div className="insp-col insp-scale">
        <label>How big is a pixel?</label>
        <div className="scalebox">
          <svg width="78" height="78" viewBox="0 0 78 78" aria-hidden>
            <rect x="1.5" y="1.5" width="75" height="75" rx="2" fill="#e8f0fe" stroke="#1a73e8" strokeWidth="1.5" strokeDasharray="4 3" />
            <rect x={39 - fieldPx / 2 + 9} y={39 - fieldPx / 2 - 6} width={fieldPx} height={fieldPx * 0.62} fill="#188038" />
            <path d={`M${39 + 9} ${39 - 6 + fieldPx} L 58 62`} stroke="#5f6368" strokeWidth="0.8" />
            <text x="50" y="70" fontSize="8" fill="#3c4043" fontFamily="Inter, sans-serif">your field</text>
          </svg>
          <div>
            <div><i className="k smap" />SMAP soil-moisture cell: <b>9 km</b></div>
            <div><i className="k field" />This block's cells: <b>30 m</b></div>
            <p>90,000 of these cells fit in one SMAP cell. Soil moisture describes the neighbourhood, not this field.</p>
          </div>
        </div>
      </div>
      <div className="insp-col insp-cell">
        <label>{cell ? `Cell row ${cell.row + 1}, column ${cell.col + 1}` : 'Cell readout'}</label>
        {cell ? (
          <dl>
            <div className={measure === 'ndvi' ? 'on' : ''}><dt>Cover</dt><dd><b>{cell.ndvi.toFixed(2)}</b> NDVI · {cell.cover_class}</dd></div>
            <div className={measure === 'et' ? 'on' : ''}><dt>Water use</dt><dd><b>{cell.et_mm_day.toFixed(1)}</b> mm/day · {fmt(mmToIn(cell.et_mm_day), 2)} in</dd></div>
            <div className={measure === 'stress' ? 'on' : ''}><dt>Heat</dt><dd><b>{cell.lst_anom_k > 0 ? '+' : ''}{cell.lst_anom_k.toFixed(1)}</b> K vs field{cell.stress_hotspot && <em>stress hotspot</em>}</dd></div>
          </dl>
        ) : (
          <p className="insp-empty">Click any block on the map to read its values.</p>
        )}
      </div>
      <button className="iconbtn insp-close" onClick={onExit} aria-label="Leave 3D view" title="Back to flat map"><Icon name="close" size={15} /></button>
    </div>
  );
}
