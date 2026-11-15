import { motionOff, usePrefs } from './a11y/prefs';
import { t, locale } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import type maplibregl from 'maplibre-gl';

const DAYS = 7;
const FRAME_MS = 600;
const iso = (d: Date) => d.toISOString().slice(0, 10);
const URL = (day: string) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate/default/${day}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png`;
const LEGEND = ['#a6d3ff', '#4aa3f0', '#1f6fd0', '#2fb35a', '#f2d230', '#f08a1c', '#d12a2a'];
const LEGEND_LABELS = ['0.1', '0.5', '1', '2', '4', '8', '16+'];

/** Last seven days of NASA GPM IMERG rain from GIBS: one raster source per day, opacity-cycled, under the field outline and 3D cells. */
export default function RainLayer(p: { map: maplibregl.Map | null; ready: boolean; on: boolean; leftInset: number; bottomInset: number }) {
  const [idx, setIdx] = useState(DAYS - 1);
  const paused = usePrefs().pause;
  const reduced = paused || motionOff();
  const [playing, setPlaying] = useState(!reduced);
  useEffect(() => { if (paused) setPlaying(false); }, [paused]);
  const days = useRef<string[]>([]);
  if (!days.current.length) { const now = Date.now(); days.current = Array.from({ length: DAYS }, (_, i) => iso(new Date(now - (DAYS - i + 1) * 864e5))); } // newest = 2 days back (IMERG latency)

  // sources and layers: all seven preloaded at opacity 0
  useEffect(() => {
    const map = p.map;
    if (!map || !p.ready || !p.on) return;
    const before = ['res-casing', 'fp-fill'].find((id) => map.getLayer(id));
    days.current.forEach((d, i) => {
      if (!map.getSource(`rain-${i}`)) map.addSource(`rain-${i}`, { type: 'raster', tiles: [URL(d)], tileSize: 256, maxzoom: 6, attribution: 'NASA GPM IMERG via GIBS' });
      if (!map.getLayer(`rain-${i}`)) map.addLayer({ id: `rain-${i}`, type: 'raster', source: `rain-${i}`, paint: { 'raster-opacity': i === DAYS - 1 ? 0.8 : 0, 'raster-resampling': 'nearest' } }, before);
    });
    return () => { days.current.forEach((_, i) => { if (map.getLayer(`rain-${i}`)) map.removeLayer(`rain-${i}`); if (map.getSource(`rain-${i}`)) map.removeSource(`rain-${i}`); }); };
  }, [p.map, p.ready, p.on]);

  useEffect(() => {
    const map = p.map;
    if (!map || !p.ready || !p.on) return;
    days.current.forEach((_, i) => { if (map.getLayer(`rain-${i}`)) map.setPaintProperty(`rain-${i}`, 'raster-opacity', i === idx ? 0.8 : 0); });
  }, [p.map, p.ready, p.on, idx]);

  useEffect(() => {
    if (!p.on || !playing) return;
    const h = setInterval(() => setIdx((i) => (i + 1) % DAYS), FRAME_MS);
    return () => clearInterval(h);
  }, [p.on, playing]);

  useEffect(() => {
    const map = p.map;
    if (!map) return;
    const stop = (e: unknown) => { if ((e as { originalEvent?: unknown }).originalEvent) setPlaying(false); };
    map.on('dragstart', stop);
    return () => { map.off('dragstart', stop); };
  }, [p.map]);

  if (!p.on) return null;
  const label = new Date(days.current[idx] + 'T12:00:00Z').toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' });
  return (
    <div className="rain-box" style={{ left: p.leftInset + 16, bottom: p.bottomInset + 58 }} data-testid="rain-box">
      <div className="rain-row">
        <button className="rain-btn" onClick={() => setPlaying(!playing)} aria-label={playing ? t('rain.pause') : t('rain.play')} data-testid="rain-play">{playing ? '❚❚' : '▶'}</button>
        {reduced && !playing && <button className="rain-btn" onClick={() => setIdx((i) => (i + 1) % DAYS)} aria-label={t('rain.next')} data-testid="rain-step">{t('rain.nextBtn')}</button>}
        <b data-testid="rain-date" aria-live="off">{label}</b>
      </div>
      <div className="rain-bar" aria-hidden="true">{LEGEND.map((c) => <i key={c} style={{ background: c }} />)}</div>
      <div className="rain-ticks" aria-hidden="true">{LEGEND_LABELS.map((l) => <span key={l}>{l}</span>)}</div>
      <small>{t('rain.rate')}</small>
      <small>NASA GPM IMERG via GIBS</small>
    </div>
  );
}
