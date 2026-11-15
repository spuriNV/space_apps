// Worldwide rain forecast: ECCC GeoMet's GDPS global model (15 km, keyless) as tiled WMS, so it covers whatever is in
// view at any zoom (US, Canada, the world). One raster source, retimed with setTiles; nothing loads until the layer is on.
import { useEffect, useRef, useState } from 'react';
import type maplibregl from 'maplibre-gl';
import Icon from '../Icons';
import { motionOff, usePrefs } from '../a11y/prefs';

const WMS = 'https://geo.weather.gc.ca/geomet';
const LAYER = 'GDPS_15km_Precip-Accum6h';
const SRC = 'rain-global';
const MAX_STEPS = 28; // 7 days of 6-hour totals
export const GLOBAL_STEPS: { from: string; color: string }[] = [
  { from: '0.1', color: '#000080' }, { from: '0.5', color: '#0000cd' }, { from: '1', color: '#0030ff' }, { from: '2.5', color: '#0090ff' },
  { from: '5', color: '#00c8ff' }, { from: '10', color: '#00ffe0' }, { from: '15', color: '#60ff90' }, { from: '20', color: '#b0ff50' },
  { from: '25', color: '#ffff00' }, { from: '30', color: '#ffa500' }, { from: '40', color: '#ff4500' }, { from: '50', color: '#ff0000' }, { from: '75+', color: '#a00000' },
];
const tiles = (time: string) => [`${WMS}?service=WMS&version=1.3.0&request=GetMap&layers=${LAYER}&styles=PRECIPMM&crs=EPSG:3857&bbox={bbox-epsg-3857}&width=256&height=256&format=image/png&transparent=true&time=${time}`];
const words = (iso: string) => { const a = new Date(iso), b = new Date(a.getTime() + 6 * 3600e3); return `${a.toLocaleString('en-US', { weekday: 'short', hour: 'numeric' })} to ${b.toLocaleString('en-US', { hour: 'numeric' })}`; };

/** The 6-hour valid times of the latest GDPS run, from a one-layer GetCapabilities (17 KB). */
async function loadTimes(): Promise<string[]> {
  const r = await fetch(`${WMS}?service=WMS&version=1.3.0&request=GetCapabilities&layer=${LAYER}`);
  const m = /name="time"[^>]*>([^<]+)</.exec(await r.text());
  const now = Date.now() - 6 * 3600e3;
  return (m?.[1] ?? '').split(',').map((s) => s.trim()).filter((s) => s && Date.parse(s) > now).slice(0, MAX_STEPS);
}

/** Map layer plus the bottom timeline (play, scrub). Renders nothing and loads nothing while off. */
export default function GlobalRain(p: { map: maplibregl.Map | null; ready: boolean; on: boolean; left: string; onState: (s: 'loading' | 'ready' | 'error') => void }) {
  const [times, setTimes] = useState<string[] | null>(null);
  const [step, setStep] = useState(0);
  const paused = usePrefs().pause;
  const [playing, setPlaying] = useState(false);
  const onState = useRef(p.onState); onState.current = p.onState;
  useEffect(() => { if (paused || motionOff()) setPlaying(false); }, [paused]);
  useEffect(() => {
    if (!p.on) { setPlaying(false); return; }
    if (times) { onState.current('ready'); return; }
    onState.current('loading');
    let ok = true;
    loadTimes().then((t) => { if (!ok) return; if (t.length) { setTimes(t); onState.current('ready'); } else onState.current('error'); }).catch(() => ok && onState.current('error'));
    return () => { ok = false; };
  }, [p.on, times]);
  const time = times?.[step];
  useEffect(() => {
    const map = p.map;
    if (!map || !p.ready || !p.on || !time) return;
    const src = map.getSource(SRC) as maplibregl.RasterTileSource | undefined;
    if (src) { src.setTiles(tiles(time)); return; }
    map.addSource(SRC, { type: 'raster', tiles: tiles(time), tileSize: 256, maxzoom: 8, attribution: 'ECCC GeoMet, GDPS global model' });
    map.addLayer({ id: SRC, type: 'raster', source: SRC, paint: { 'raster-opacity': 0.75, 'raster-resampling': 'linear', 'raster-fade-duration': 0 } }, ['rain-fill', 'res-casing', 'fp-fill'].find((id) => map.getLayer(id)));
  }, [p.map, p.ready, p.on, time]);
  useEffect(() => {
    const map = p.map;
    if (!map || p.on) return;
    if (map.getLayer(SRC)) map.removeLayer(SRC);
    if (map.getSource(SRC)) map.removeSource(SRC);
  }, [p.map, p.on]);
  useEffect(() => {
    if (!p.on || !playing || !times) return;
    const h = setInterval(() => setStep((k) => (k + 1) % times.length), 1200);
    return () => clearInterval(h);
  }, [p.on, playing, times]);
  if (!p.on || !times) return null;
  const days = times.map((t, k) => ({ k, d: new Date(t) })).filter(({ k, d }) => k === 0 || (k > 2 && d.getHours() < 6));
  return (
    <div className="rain-tl" style={{ left: p.left }} data-testid="rain-timeline">
      <button className="icon-btn play" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play the next 7 days'} data-testid="rain-play"><Icon name={playing ? 'pause' : 'play'} size={20} /></button>
      <div className="tl-body">
        <p className="tl-now" aria-live="polite"><b data-testid="rain-when">{words(times[step])}</b></p>
        <input type="range" min={0} max={times.length - 1} step={1} value={step} onChange={(e) => { setPlaying(false); setStep(+e.target.value); }} aria-label="Forecast time" aria-valuetext={words(times[step])} data-testid="rain-scrub" />
        <div className="tl-days" aria-hidden="true">
          {days.map(({ k, d }) => <span key={k} style={{ left: `${(k / Math.max(1, times.length - 1)) * 100}%` }}>{k === 0 ? 'Now' : d.toLocaleString('en-US', { weekday: 'short' })}</span>)}
        </div>
      </div>
    </div>
  );
}
