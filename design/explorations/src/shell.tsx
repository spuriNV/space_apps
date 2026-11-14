import { ReactNode } from 'react';
import { CAL, CLS, Cls, YEARS, cropOf, daysIn, simple } from './data';

/* ---------- satellite background (Esri World Imagery, no key) with the real DWR field outline ---------- */
const FIELD: [number, number][] = [[-122.08658, 39.13788], [-122.07894, 39.1379], [-122.07887, 39.13974], [-122.07884, 39.14404], [-122.07897, 39.14475], [-122.07953, 39.14489], [-122.08755, 39.14492], [-122.08777, 39.14469], [-122.08783, 39.13826], [-122.08768, 39.13789]];
const Z = 16;
const px = (lon: number, lat: number) => {
  const s = 256 * 2 ** Z;
  const r = (lat * Math.PI) / 180;
  return [((lon + 180) / 360) * s, ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * s];
};
export function Satellite({ cx, cy, label = true }: { cx: number; cy: number; label?: boolean }) {
  const [fx, fy] = px(-122.08334, 39.14139);
  const ox = fx - cx, oy = fy - cy; // world px at screen (0,0)
  const tiles: ReactNode[] = [];
  for (let tx = Math.floor(ox / 256); tx * 256 < ox + 1440; tx++)
    for (let ty = Math.floor(oy / 256); ty * 256 < oy + 900; ty++)
      tiles.push(<img key={`${tx}-${ty}`} alt="" src={`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${Z}/${ty}/${tx}`} style={{ left: tx * 256 - ox, top: ty * 256 - oy }} />);
  const pts = FIELD.map(([lo, la]) => px(lo, la)).map(([x, y]) => `${x - ox},${y - oy}`).join(' ');
  return (
    <div className="sat">
      {tiles}
      <div className="sat-shade" />
      <svg className="sat-svg" width={1440} height={900}>
        <polygon points={pts} fill="rgba(255,209,102,0.08)" stroke="#ffd166" strokeWidth={2} />
      </svg>
      {label && <div className="sat-label" style={{ left: cx, top: cy - 205 }}>Your field · Colusa County · 60 ha (149 acres)</div>}
    </div>
  );
}

/* ---------- left rail (as in variant B) ---------- */
const ICON: Record<string, string> = {
  Fields: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  Year: 'M5 5h14v15H5zM5 9h14M9 3v4M15 3v4',
  Trends: 'M3 17l6-6 4 4 8-8',
  Compare: 'M6 20V10M12 20V4M18 20v-7',
  Brief: 'M6 3h9l4 4v14H6zM9 12h7M9 16h7',
};
export function Rail({ on }: { on: 'Year' | 'Compare' }) {
  return (
    <nav className="rail glass">
      <div className="rail-logo"><span>FS</span></div>
      {Object.entries(ICON).map(([k, d]) => (
        <div key={k} className={`rail-btn ${k === on ? 'on' : ''}`}>
          <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round"><path d={d} /></svg>
          <span>{k}</span>
        </div>
      ))}
    </nav>
  );
}

/* ---------- exploration switcher (not part of the product) ---------- */
export const OPTIONS = {
  year: ['One year, round the clock', 'Ten years, one pattern', 'Two hard years'],
  compare: ['Trade-offs in words', 'Gain / give up vs today', 'Head-to-head'],
};
export function Switcher({ screen, opt }: { screen: 'year' | 'compare'; opt: number }) {
  return (
    <div className="switcher glass">
      <span className="sw-tag">Exploration</span>
      {(['year', 'compare'] as const).map((s) => (
        <div key={s} className="sw-group">
          <b>{s === 'year' ? "Field's year" : 'Compare'}</b>
          {OPTIONS[s].map((name, i) => (
            <a key={i} href={`?screen=${s}&opt=${i + 1}`} className={s === screen && i + 1 === opt ? 'on' : ''} title={name}>{i + 1}</a>
          ))}
        </div>
      ))}
      <span className="sw-name">{OPTIONS[screen][opt - 1]}</span>
    </div>
  );
}

/* ---------- bottom year scrubber (variant B's timeline, simplified) ---------- */
export function YearStrip({ selected, onPick, mode = 'simple' }: { selected?: number[]; onPick?: (y: number) => void; mode?: 'simple' | 'full' }) {
  return (
    <div className="ys">
      {CAL.map((yc) => (
        <button key={yc.year} className={`ys-year ${selected?.includes(yc.year) ? 'on' : ''}`} onClick={() => onPick?.(yc.year)} disabled={!onPick}>
          <svg viewBox={`0 0 ${daysIn(yc.year)} 10`} preserveAspectRatio="none">
            {yc.segments.map((s, i) => {
              const c = (mode === 'simple' ? simple(s.class as Cls) : (s.class as Cls));
              return <rect key={i} x={s.start_doy - 1} width={s.days} height={10} fill={CLS[c].color} />;
            })}
          </svg>
          <span>{yc.year}<small>{cropOf(yc.year) === 'Rice' ? '' : ' fallow'}</small></span>
        </button>
      ))}
    </div>
  );
}
export function BottomBar({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <div className="bottom glass">
      <div className="bb-play"><svg width={20} height={20} viewBox="0 0 24 24"><path d="M8 5v14l11-7z" fill="currentColor" /></svg></div>
      <div className="bb-title"><b>{title}</b><span>{sub}</span></div>
      <div className="bb-body">{children}</div>
    </div>
  );
}
export { YEARS };
