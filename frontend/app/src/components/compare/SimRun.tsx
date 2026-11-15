// Farmer-run year sim: pick a rotation + weather year, then watch cover and water play on the map timeline.
import type { Location, RotationStrategy } from '../../types';
import { mmToAfac, tOf } from '../../lib';
import { isBC } from '../ui/shared';
import type { SimMode } from '../ui/FieldTimeline';
import Icon from '../Icons';

type Weather = 'typical' | '2022' | '2023';

const labels = (bc: boolean): Record<Weather, string> => bc
  ? { typical: 'Typical year', '2022': 'Drier year (2022 weather)', '2023': 'Restricted water (like 2023)' }
  : { typical: 'Typical year', '2022': 'Dry like 2022', '2023': 'Wet like 2023' };

function needAf(s: RotationStrategy, w: Weather) {
  const r = w === 'typical' ? null : s.exposure.replay[w]?.irrigation_need_mm;
  return mmToAfac((r ?? s.water.irrigation_need_mm).value);
}

export function SimRun(p: {
  loc: Location;
  strategies: RotationStrategy[];
  allocation: number;
  pickId: string | null;
  weather: Weather;
  setWeather: (w: Weather) => void;
  onRun: (sim: NonNullable<SimMode>, startT: number) => void;
  running: boolean;
  onStop: () => void;
}) {
  const bc = isBC(p.loc);
  const L = labels(bc);
  const s = p.strategies.find((x) => x.id === p.pickId) ?? p.strategies.find((x) => !x.is_baseline) ?? p.strategies[0];
  if (!s) return null;
  const year = p.weather === 'typical' ? 2024 : +p.weather;
  const need = needAf(s, p.weather);
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
    <div className="c2-in-block sim-run" data-testid="sim-run">
      <h3>Play a year on the map</h3>
      <p className="how">Watch the field’s cover change month by month, and its water use against your limit.</p>
      <div className="seg small wrap" role="group" aria-label="Weather year for the sim">
        {(['typical', '2022', '2023'] as Weather[]).map((w) => (
          <button key={w} type="button" className={p.weather === w ? 'on' : ''} onClick={() => p.setWeather(w)} data-testid={`sim-weather-${w}`}>
            {L[w]}
          </button>
        ))}
      </div>
      <p className="sim-preview">
        <b>{s.short_name}</b> · ~{need.toFixed(1)} acre-ft/acre vs your {p.allocation.toFixed(1)} limit
        {need > p.allocation ? <em className="over"> · short by {(need - p.allocation).toFixed(1)}</em> : <em className="ok"> · fits</em>}
      </p>
      {p.running ? (
        <button type="button" className="btn wide" onClick={p.onStop} data-testid="sim-stop">Stop sim</button>
      ) : (
        <button type="button" className="btn primary wide" onClick={start} data-testid="sim-start">
          Play {year} on the map<Icon name="play" size={16} />
        </button>
      )}
    </div>
  );
}
