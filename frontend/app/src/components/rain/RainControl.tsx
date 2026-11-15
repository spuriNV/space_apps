// "Rain & drought" on the map, after Windy's layer pattern: one button opens a card with a layer switch.
//   Rain forecast: Total (24 h / 3 / 5 / 7 days) or Hour by hour, which docks a timeline at the bottom of the map (play,
//   scrub, day marks, the time in words) and steps through NOAA's twelve 6-hour forecasts for the next 3 days.
//   Drought now: the weekly U.S. Drought Monitor, D0-D4.
// Colours: one hue each, light to dark (dataviz ordinal check passes against satellite imagery). Data: backend app/rain.
import { utc, type DroughtNow, type RainDays, type RainForecast } from '../../api';
import Icon from '../Icons';
import { Seg } from '../ui/Seg';
import { locale, t } from '../../i18n';

export const RAIN_STEPS: { from: number; label: string; color: string }[] = [
  { from: 0.01, label: t('merge.rain.trace'), color: '#cfe3f6' },
  { from: 0.1, label: '0.1', color: '#a4cbee' },
  { from: 0.25, label: '0.25', color: '#76ade3' },
  { from: 0.5, label: '0.5', color: '#4b8fd6' },
  { from: 1, label: '1', color: '#2a6fbf' },
  { from: 2, label: '2', color: '#1c519b' },
  { from: 3, label: '3+', color: '#173873' },
];
export const RAIN_COLOR = ['step', ['get', 'qpf'], RAIN_STEPS[0].color, ...RAIN_STEPS.slice(1).flatMap((s) => [s.from, s.color])];
export const DROUGHT_STEPS: { dm: number; label: string; name: string; color: string }[] = [
  { dm: 0, label: 'D0', name: t('merge.rain.d0'), color: '#ffff00' },
  { dm: 1, label: 'D1', name: t('merge.rain.d1'), color: '#fcd37f' },
  { dm: 2, label: 'D2', name: t('merge.rain.d2'), color: '#ffaa00' },
  { dm: 3, label: 'D3', name: t('merge.rain.d3'), color: '#e60000' },
  { dm: 4, label: 'D4', name: t('merge.rain.d4'), color: '#730000' },
];
export const DROUGHT_COLOR = ['match', ['get', 'dm'], ...DROUGHT_STEPS.flatMap((s) => [s.dm, s.color]), '#999'];

/** Which drought map suits the view: the U.S. and Canadian monitors across North America, NASA soil moisture elsewhere. */
export const droughtRegion = (lat: number, lon: number): 'na' | 'gl' => (lat >= 15 && lat <= 75 && lon >= -170 && lon <= -50 ? 'na' : 'gl');
export type WxLayer = 'rain' | 'drought' | 'past';
export type RainMode = 'total' | 'hourly';
const when = (d: Date | null, o: Intl.DateTimeFormatOptions) => (d ? d.toLocaleString(locale, o) : '');
const HOUR: Intl.DateTimeFormatOptions = { weekday: 'short', hour: 'numeric' };
/** "Mon 4 PM to 10 PM" for a 6-hour step. */
export const stepWords = (f: RainForecast | null) => { const a = utc(f?.valid_from), b = utc(f?.valid_to); return a && b ? t('merge.rain.to', { a: when(a, HOUR), b: when(b, { hour: 'numeric' }) }) : ''; };

export function WeatherControl(p: {
  on: boolean; setOn: (v: boolean) => void; layer: WxLayer; setLayer: (l: WxLayer) => void;
  mode: RainMode; setMode: (m: RainMode) => void; days: RainDays; setDays: (d: RainDays) => void;
  rain: RainForecast | null; drought: DroughtNow | null; region: 'na' | 'gl'; state: 'idle' | 'loading' | 'ready' | 'error'; retry: () => void;
}) {
  const issued = utc(p.rain?.issued), to = utc(p.rain?.valid_to);
  const last = to ? new Date(to.getTime() - 1) : null; // valid_to is midnight UTC: the day before, locally
  return (
    <div className="rain-ctl" data-testid="rain-ctl">
      <button className={`map-tool rain-btn ${p.on ? 'on' : ''}`} onClick={() => p.setOn(!p.on)} aria-pressed={p.on} aria-expanded={p.on} aria-label={t('merge2.rainAria')} title={t('merge2.rainAria')} data-testid="rain-btn">
        <Icon name="drop" size={18} /><span>{t('merge.rain.btn')}</span>
      </button>
      {p.on && (
        <section className="rain-card" aria-label={t('merge.rain.cardAria')} data-testid="rain-card" onKeyDown={(e) => { if (e.key === 'Escape') p.setOn(false); }}>
          <button className="rain-x" onClick={() => p.setOn(false)} aria-label={t('merge2.rainClose')} title={t('merge2.close')} data-testid="rain-close"><Icon name="close" size={18} /></button>
          <Seg className="rain-layers" label={t('merge.rain.layerAria')} value={p.layer} onChange={p.setLayer} options={[{ v: 'rain', label: t('merge2.lForecast'), testid: 'wx-rain' }, { v: 'drought', label: t('merge2.lDrought'), testid: 'wx-drought' }, { v: 'past', label: t('merge.rain.lPast'), testid: 'wx-past' }]} />
          {p.layer === 'rain' ? <>
            <div className="rain-row">
              <Seg className="small" label={t('merge.rain.showAria')} value={p.mode} onChange={p.setMode} options={[{ v: 'total', label: t('merge.rain.total'), testid: 'rain-total' }, { v: 'hourly', label: t('merge.rain.hourly'), testid: 'rain-hourly' }]} />
            </div>
            {p.mode === 'total' && <Seg className="small" label={t('merge.rain.periodAria')} value={p.days} onChange={p.setDays} options={[{ v: 1, label: t('merge.rain.h24') }, { v: 3, label: t('merge.rain.dd3') }, { v: 5, label: t('merge.rain.dd5') }, { v: 7, label: t('merge.rain.dd7') }]} />}
            <p className="rain-title">{p.mode === 'total' ? <>{t('merge.rain.titleTotal')}{last ? <small>{t('merge.rain.through', { d: when(last, { weekday: 'short', month: 'short', day: 'numeric' }) })}</small> : null}</> : <>{t('merge.rain.titleHourly')}<small>{t('merge.rain.hourlyHint')}</small></>}</p>
            <ol className="rain-legend" aria-label={t('merge.rain.legendIn')}>
              {RAIN_STEPS.map((s) => <li key={s.from}><i style={{ background: s.color }} /><span>{s.label}</span></li>)}
            </ol>
            <p className="rain-src" role="status">
              {p.state === 'loading' ? t('merge.rain.loadFc') : p.state === 'error' ? t('merge.rain.errFc') : <>{t('merge.rain.issued', { d: when(issued, { weekday: 'short', hour: 'numeric', minute: '2-digit' }) })}{p.rain?.stale ? t('merge.rain.stale') : ''}{t('merge.rain.fcNote')}</>}
            </p>
          </> : p.layer === 'past' ? <>
            <p className="rain-title">{t('merge.rain.past7')}<small>{t('merge.rain.past7Hint')}</small></p>
            <p className="rain-src">{t('merge.rain.pastSrc')}</p>
          </> : <>
            <p className="rain-title">{p.region === 'na' ? t('merge.rain.droughtNow') : t('merge.rain.soilNow')}</p>
            {p.region === 'na' ? <>
            <ol className="drought-legend" aria-label={t('merge.rain.legendDm')}>
              {DROUGHT_STEPS.map((s) => <li key={s.dm}><i style={{ background: s.color }} /><b>{s.label}</b><span>{s.name}{s.dm > 0 ? t('merge.rain.drought') : ''}</span></li>)}
            </ol>
            <p className="rain-src" role="status">
              {p.state === 'loading' ? t('merge.rain.loadDm') : p.state === 'error' ? <>{t('merge2.dmErr')} <button className="rain-retry" onClick={p.retry} data-testid="drought-retry">{t('merge2.tryAgain')}</button></> : <>{t('merge.rain.dmUS')}{p.drought?.map_date ? t('merge.rain.dmMap', { d: when(new Date(p.drought.map_date + 'T12:00:00'), { month: 'short', day: 'numeric' }) }) : t('merge.rain.dmNo')}{t('merge.rain.dmRest')}</>}
            </p></> : <>
            <p className="rain-src">{t('merge.rain.smap')}</p>
            <p className="rain-src">{t('merge.rain.smapSrc')}</p></>}
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
      <button className="icon-btn play" onClick={() => p.setPlaying(!p.playing)} aria-label={p.playing ? t('merge.rain.pause') : t('merge.rain.play3')} disabled={p.loaded < p.steps.length} data-testid="rain-play"><Icon name={p.playing ? 'pause' : 'play'} size={20} /></button>
      <div className="tl-body">
        <p className="tl-now" aria-live="polite"><b>{cur ? stepWords(cur) : t('merge.rain.loading')}</b>{p.loaded < p.steps.length && <small> {t('merge.rain.loadN', { n: p.loaded, m: p.steps.length })}</small>}</p>
        <input type="range" min={0} max={p.steps.length - 1} step={1} value={p.step} onChange={(e) => { p.setPlaying(false); p.setStep(+e.target.value); }} aria-label={t('merge.rain.fcTime')} aria-valuetext={cur ? stepWords(cur) : undefined} data-testid="rain-scrub" />
        <div className="tl-days" aria-hidden="true">
          {marks.map((d, k) => (d.getHours() < 6 || k === 0) && <span key={k} style={{ left: `${(k / 12) * 100}%` }}>{k === 0 ? t('merge.rain.now') : d.toLocaleString(locale, { weekday: 'short' })}</span>)}
        </div>
      </div>
    </div>
  );
}
