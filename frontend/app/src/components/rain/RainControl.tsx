// "Rain & drought" on the map, after Windy's layer pattern: one button opens a card with a layer switch.
//   Rain forecast: Total (24 h / 3 / 5 / 7 days) or Hour by hour, which docks a timeline at the bottom of the map (play,
//   scrub, day marks, the time in words) and steps through NOAA's twelve 6-hour forecasts for the next 3 days.
//   Drought now: the weekly U.S. Drought Monitor, D0-D4.
// Colours: one hue each, light to dark (dataviz ordinal check passes against satellite imagery). Data: backend app/rain.
import { utc, type DroughtNow, type RainDays, type RainForecast } from '../../api';
import Icon from '../Icons';
import { Seg } from '../ui/Seg';

export const RAIN_STEPS: { from: number; label: string; color: string }[] = [
  { from: 0.01, label: 'Trace', color: '#cfe3f6' },
  { from: 0.1, label: '0.1', color: '#a4cbee' },
  { from: 0.25, label: '0.25', color: '#76ade3' },
  { from: 0.5, label: '0.5', color: '#4b8fd6' },
  { from: 1, label: '1', color: '#2a6fbf' },
  { from: 2, label: '2', color: '#1c519b' },
  { from: 3, label: '3+', color: '#173873' },
];
export const RAIN_COLOR = ['step', ['get', 'qpf'], RAIN_STEPS[0].color, ...RAIN_STEPS.slice(1).flatMap((s) => [s.from, s.color])];
export const DROUGHT_STEPS: { dm: number; label: string; name: string; color: string }[] = [
  { dm: 0, label: 'D0', name: 'Abnormally dry', color: '#ffff00' },
  { dm: 1, label: 'D1', name: 'Moderate', color: '#fcd37f' },
  { dm: 2, label: 'D2', name: 'Severe', color: '#ffaa00' },
  { dm: 3, label: 'D3', name: 'Extreme', color: '#e60000' },
  { dm: 4, label: 'D4', name: 'Exceptional', color: '#730000' },
];
export const DROUGHT_COLOR = ['match', ['get', 'dm'], ...DROUGHT_STEPS.flatMap((s) => [s.dm, s.color]), '#999'];

/** Which drought map suits the view: the U.S. and Canadian monitors across North America, NASA soil moisture elsewhere. */
export const droughtRegion = (lat: number, lon: number): 'na' | 'gl' => (lat >= 15 && lat <= 75 && lon >= -170 && lon <= -50 ? 'na' : 'gl');
export type WxLayer = 'rain' | 'drought' | 'past';
export type RainMode = 'total' | 'hourly';
const when = (d: Date | null, o: Intl.DateTimeFormatOptions) => (d ? d.toLocaleString('en-US', o) : '');
const HOUR: Intl.DateTimeFormatOptions = { weekday: 'short', hour: 'numeric' };
/** "Mon 4 PM to 10 PM" for a 6-hour step. */
export const stepWords = (f: RainForecast | null) => { const a = utc(f?.valid_from), b = utc(f?.valid_to); return a && b ? `${when(a, HOUR)} to ${when(b, { hour: 'numeric' })}` : ''; };

export function WeatherControl(p: {
  on: boolean; setOn: (v: boolean) => void; layer: WxLayer; setLayer: (l: WxLayer) => void;
  mode: RainMode; setMode: (m: RainMode) => void; days: RainDays; setDays: (d: RainDays) => void;
  rain: RainForecast | null; drought: DroughtNow | null; region: 'na' | 'gl'; state: 'idle' | 'loading' | 'ready' | 'error'; right: number;
}) {
  const issued = utc(p.rain?.issued), to = utc(p.rain?.valid_to);
  const last = to ? new Date(to.getTime() - 1) : null; // valid_to is midnight UTC: the day before, locally
  return (
    <div className="rain-ctl" style={{ right: p.right }} data-testid="rain-ctl">
      <button className={`rain-btn ${p.on ? 'on' : ''}`} onClick={() => p.setOn(!p.on)} aria-pressed={p.on} aria-expanded={p.on} data-testid="rain-btn">
        <Icon name="drop" size={18} />Rain &amp; drought
      </button>
      {p.on && (
        <section className="rain-card" aria-label="Rain and drought map" data-testid="rain-card">
          <Seg label="Map layer" value={p.layer} onChange={p.setLayer} options={[{ v: 'rain', label: 'Rain forecast', testid: 'wx-rain' }, { v: 'drought', label: 'Drought now', testid: 'wx-drought' }, { v: 'past', label: 'Past rain', testid: 'wx-past' }]} />
          {p.layer === 'rain' ? <>
            <div className="rain-row">
              <Seg className="small" label="How to show rain" value={p.mode} onChange={p.setMode} options={[{ v: 'total', label: 'Total', testid: 'rain-total' }, { v: 'hourly', label: 'Hour by hour', testid: 'rain-hourly' }]} />
            </div>
            {p.mode === 'total' && <Seg className="small" label="Forecast period" value={p.days} onChange={p.setDays} options={[{ v: 1, label: '24 h' }, { v: 3, label: '3 days' }, { v: 5, label: '5 days' }, { v: 7, label: '7 days' }]} />}
            <p className="rain-title">{p.mode === 'total' ? <>Total rain expected, inches{last ? <small>through {when(last, { weekday: 'short', month: 'short', day: 'numeric' })}</small> : null}</> : <>Rain in each 6 hours, inches<small>Play or drag the timeline at the bottom of the map</small></>}</p>
            <ol className="rain-legend" aria-label="Legend, inches">
              {RAIN_STEPS.map((s) => <li key={s.from}><i style={{ background: s.color }} /><span>{s.label}</span></li>)}
            </ol>
            <p className="rain-src" role="status">
              {p.state === 'loading' ? 'Loading the NOAA forecast…' : p.state === 'error' ? 'The NOAA forecast is not reachable right now.' : <>NOAA forecast, issued {when(issued, { weekday: 'short', hour: 'numeric', minute: '2-digit' })}{p.rain?.stale ? ' (last copy saved; NOAA is not answering)' : ''}. A forecast, not a guarantee. US only.</>}
            </p>
          </> : p.layer === 'past' ? <>
            <p className="rain-title">Rain, last 7 days<small>Animated daily rain from NASA satellites. Play it at the bottom of the map.</small></p>
            <p className="rain-src">NASA GPM IMERG via GIBS, about 10 km pixels.</p>
          </> : <>
            <p className="rain-title">{p.region === 'na' ? 'Drought now' : 'Soil moisture now (no drought monitor here)'}</p>
            {p.region === 'na' ? <>
            <ol className="drought-legend" aria-label="Legend, drought category">
              {DROUGHT_STEPS.map((s) => <li key={s.dm}><i style={{ background: s.color }} /><b>{s.label}</b><span>{s.name}{s.dm > 0 ? ' drought' : ''}</span></li>)}
            </ol>
            <p className="rain-src" role="status">
              {p.state === 'loading' ? 'Loading the Drought Monitor map…' : <>United States: U.S. Drought Monitor{p.drought?.map_date ? `, map of ${when(new Date(p.drought.map_date + 'T12:00:00'), { month: 'short', day: 'numeric' })}` : ' (not reachable right now)'}, updated Thursdays. Canada: Canadian Drought Monitor (Agriculture and Agri-Food Canada), updated monthly. Same D0 to D4 scale. No colour means no drought.</>}
            </p></> : <>
            <p className="rain-src">Yellow and orange are drier soil, green and blue are wetter. NASA SMAP root-zone soil moisture, about 9 km pixels, a few days behind. Pan to North America for the official drought monitors.</p>
            <p className="rain-src">Source: NASA SMAP L4 via GIBS.</p></>}
          </>}
        </section>
      )}
    </div>
  );
}

/** Windy-style timeline docked at the bottom of the map: play, a scrubber over the next 72 hours with day marks, the time in words. */
export function RainTimeline(p: { step: number; setStep: (k: number) => void; playing: boolean; setPlaying: (v: boolean) => void; steps: (RainForecast | null)[]; loaded: number; left: string }) {
  const first = utc(p.steps[0]?.valid_from);
  const marks = first ? Array.from({ length: 13 }, (_, k) => new Date(first.getTime() + k * 6 * 3600e3)) : [];
  const cur = p.steps[p.step] ?? null;
  return (
    <div className="rain-tl" style={{ left: p.left }} data-testid="rain-timeline">
      <button className="icon-btn play" onClick={() => p.setPlaying(!p.playing)} aria-label={p.playing ? 'Pause' : 'Play the next 3 days'} disabled={p.loaded < p.steps.length} data-testid="rain-play"><Icon name={p.playing ? 'pause' : 'play'} size={20} /></button>
      <div className="tl-body">
        <p className="tl-now" aria-live="polite"><b>{cur ? stepWords(cur) : 'Loading…'}</b>{p.loaded < p.steps.length && <small> Loading {p.loaded} of {p.steps.length}…</small>}</p>
        <input type="range" min={0} max={p.steps.length - 1} step={1} value={p.step} onChange={(e) => { p.setPlaying(false); p.setStep(+e.target.value); }} aria-label="Forecast time" aria-valuetext={cur ? stepWords(cur) : undefined} data-testid="rain-scrub" />
        <div className="tl-days" aria-hidden="true">
          {marks.map((d, k) => (d.getHours() < 6 || k === 0) && <span key={k} style={{ left: `${(k / 12) * 100}%` }}>{k === 0 ? 'Now' : d.toLocaleString('en-US', { weekday: 'short' })}</span>)}
        </div>
      </div>
    </div>
  );
}
