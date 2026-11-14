import { getCells, mmToIn } from '../api';
import { MEASURES, gradientCss, type MeasureKey } from '../measures';
import type { CellProps, Location } from '../types';
import { Icon, fmt } from './Bits';

export default function Inspector({ loc, measure, onMeasure, cell, onExit }: { loc: Location; measure: MeasureKey; onMeasure: (m: MeasureKey) => void; cell: CellProps | null; onExit: () => void }) {
  const m = MEASURES[measure];
  const grid = getCells(loc.id);
  const n = grid.features.length;
  const fieldPx = Math.max(5, Math.round(((loc.grid.cols * 30) / 9000) * 63));
  return (
    <div className="inspector" data-testid="inspector">
      <div className="insp-col insp-layers">
        <div className="insp-title"><Icon name="cube" size={16} /><b>Field block</b><span>{n} cells</span></div>
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
        <div className="grad-ends"><span>{m.fmt(m.domain[0])}<br />{m.lowLabel}</span><span>{m.fmt(m.domain[1])} {m.unit}<br />{m.highLabel}</span></div>
        <div className="insp-src">Taller block = higher value<br />{m.source} · {grid.scene_date}</div>
      </div>
      <div className="insp-col insp-scale">
        <label>How big is a pixel?</label>
        <div className="scalebox">
          <svg width="66" height="66" viewBox="0 0 66 66" aria-hidden>
            <rect x="1.5" y="1.5" width="63" height="63" rx="2" fill="#e8f0fe" stroke="#1a73e8" strokeWidth="1.5" strokeDasharray="4 3" />
            <rect x={38} y={22} width={fieldPx} height={Math.max(3, fieldPx * 0.62)} fill="#188038" />
          </svg>
          <div>
            <div><i className="k smap" />SMAP cell <b>9 km</b></div>
            <div><i className="k field" />Your field, to scale</div>
            <div><i className="k cell" />One block <b>30 m</b></div>
          </div>
        </div>
        <p className="scale-note">90,000 blocks fit in one SMAP soil-moisture cell: it describes the neighbourhood, not this field.</p>
      </div>
      <div className="insp-col insp-cell">
        <label>{cell ? `Block · row ${cell.row + 1}, col ${cell.col + 1}` : 'Block readout'}</label>
        {cell ? (
          <dl>
            <div className={measure === 'ndvi' ? 'on' : ''}><dt>Cover</dt><dd><b>{cell.ndvi.toFixed(2)}</b> NDVI<small>{cell.cover_class}</small></dd></div>
            <div className={measure === 'et' ? 'on' : ''}><dt>Water use</dt><dd><b>{cell.et_mm_day.toFixed(1)}</b> mm/day<small>{fmt(mmToIn(cell.et_mm_day), 2)} in</small></dd></div>
            <div className={measure === 'stress' ? 'on' : ''}><dt>Heat</dt><dd><b>{cell.lst_anom_k > 0 ? '+' : ''}{cell.lst_anom_k.toFixed(1)}</b> K{cell.stress_hotspot ? <em>hotspot</em> : <small>vs field</small>}</dd></div>
          </dl>
        ) : (
          <p className="insp-empty">Click any block on the map to read its values.</p>
        )}
      </div>
      <button className="iconbtn insp-close" onClick={onExit} aria-label="Leave 3D view" title="Back to flat map"><Icon name="close" size={15} /></button>
    </div>
  );
}
