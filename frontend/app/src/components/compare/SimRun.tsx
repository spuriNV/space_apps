// Farmer-run year sim: uses the same weather year as Compare (dry / wet / typical), then plays cover on the map.
import type { Location, RotationStrategy } from '../../types';
import { tOf } from '../../lib';
import type { SimMode } from '../ui/FieldTimeline';
import Icon from '../Icons';
import { type Weather, weatherLabels, waterOf } from './weatherReplay';

export function SimRun(p: {
  loc: Location;
  strategies: RotationStrategy[];
  allocation: number;
  pickId: string | null;
  weather: Weather;
  onRun: (sim: NonNullable<SimMode>, startT: number) => void;
  running: boolean;
  onStop: () => void;
}) {
  const L = weatherLabels(p.loc);
  const s = p.strategies.find((x) => x.id === p.pickId) ?? p.strategies.find((x) => !x.is_baseline) ?? p.strategies[0];
  if (!s) return null;
  const year = p.weather === 'typical' ? 2024 : +p.weather;
  const need = waterOf(s, p.weather).v ?? 0;
  const start = () => {
    p.onRun({
      year,
      label: L[p.weather],
      cover: s.month_cover || 'c'.repeat(12),
      needAf: need,
      limitAf: p.allocation,
      name: s.short_name,
    }, tOf(year, 0));
  };
  return (
    <div className="sim-run" data-testid="sim-run">
      <h3>Play a year on the map</h3>
      <p className="how">Watch the field's cover change month by month. Weather year: <b>{L[p.weather]}</b> (change with the chips above).</p>
      <p className="sim-preview" data-testid="sim-preview">
        <b>{s.short_name}</b> · ~{need.toFixed(1)} acre-ft/acre vs your {p.allocation.toFixed(1)} limit
        {need > p.allocation ? <em className="over"> · short by {(need - p.allocation).toFixed(1)}</em> : <em className="ok"> · fits</em>}
      </p>
      {p.running ? (
        <button type="button" className="btn btn-outline wide" onClick={p.onStop} data-testid="sim-stop">Stop sim</button>
      ) : (
        <button type="button" className="btn btn-primary wide" onClick={start} data-testid="sim-start">
          Play {year} on the map<Icon name="play" size={16} />
        </button>
      )}
    </div>
  );
}
