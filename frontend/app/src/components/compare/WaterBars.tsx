// Compare: every rotation's yearly irrigation need as a horizontal bar against the user's water limit.
// Bars slide to new lengths when the weather year or the selected rotation changes; the selected bar's
// difference from today counts up or down in acre-feet over the whole field.
import type { RotationStrategy } from '../../types';
import { RAIN_FED } from '../../lib';
import { waterOf, type Weather } from './weatherReplay';
import { useCountUp } from '../week/useCountUp';
import '../week/weekchart.css';

export function WaterBars({ strategies, selId, todayId, weather, allocation, acres }: {
  strategies: RotationStrategy[]; selId: string; todayId: string; weather: Weather; allocation: number; acres: number;
}) {
  const rows = strategies.map((s) => { const w = waterOf(s, weather); return { s, v: w.rf ? 0 : w.v, rf: !!w.rf }; });
  const todayV = rows.find((r) => r.s.id === todayId)?.v ?? null;
  const selV = rows.find((r) => r.s.id === selId)?.v ?? null;
  const max = Math.max(allocation, ...rows.map((r) => r.v ?? 0)) * 1.1 || 1;
  const pct = (v: number) => Math.min(100, (v / max) * 100);
  const diffAf = selV != null && todayV != null && selId !== todayId ? (selV - todayV) * acres : null;
  const shown = useCountUp(diffAf ?? 0, 600);
  const rounded = Math.round(Math.abs(shown));
  return (
    <section className="cw" data-testid="water-bars" aria-label="Yearly water need against your limit">
      <h3>Water a year, against your limit</h3>
      <div className="cw-chart" role="img" aria-label={rows.map((r) => `${r.s.short_name} ${r.rf ? RAIN_FED : `${r.v?.toFixed(1)} acre-feet per acre`}`).join('; ') + `. Your limit is ${allocation.toFixed(1)}.`}>
        {rows.map((r) => (
          <div key={r.s.id} className={`cw-row ${r.s.id === selId ? 'sel' : ''} ${r.v != null && r.v > allocation ? 'over' : ''}`}>
            <span className="cw-lab" title={r.s.short_name}>{r.s.is_baseline ? 'Today' : r.s.short_name}</span>
            <div className="cw-track">
              <i className="cw-bar" style={{ '--w': r.v == null ? 0 : Math.max(r.rf ? 0 : 1, pct(r.v)) } as React.CSSProperties} />
              <i className="cw-lim" style={{ '--l': pct(allocation) } as React.CSSProperties} />
            </div>
            <span className="cw-val">{r.rf ? 'rain' : r.v != null ? r.v.toFixed(1) : '–'}</span>
          </div>
        ))}
      </div>
      <p className="cw-note dim" style={{ margin: '6px 0 0', fontSize: 'var(--fs-fine)' }}>Acre-feet per acre. Dashed line: your limit, {allocation.toFixed(1)}.</p>
      {diffAf != null && (
        <p className="cw-delta" aria-live="polite" data-testid="water-delta">
          {rounded.toLocaleString()} acre-feet {diffAf <= 0 ? 'less' : 'more'} than today
          <small>{acres.toLocaleString()} acres, {weather === 'typical' ? 'a typical year' : `the ${weather} weather year`}</small>
        </p>
      )}
    </section>
  );
}
