// The Nation panel: opens when a reserve or tribal land is clicked on the map or picked from the list.
// Name and Nation, what this land has (the tap-anywhere analysis at its centroid), the Nation tools, nearby fields, the Nation's
// own website where our data names one. Plain language, public data only; nothing here speaks for the Nation.
import { useEffect, useState } from 'react';
import * as api from '../../api';
import type { Location } from '../../types';
import Icon from '../Icons';
import { NationTools } from '../week/NationTools';
import { ThisWeek } from '../week/ThisWeek';
import { cropName, soilFacts, known } from '../ui/shared';
import { areaText, kindLabel, type LandDetail, type LandFeature } from './lands';
import './lands.css';

type Spot = { state: 'loading' } | { state: 'ok'; loc: Location } | { state: 'error'; message: string };

export function LandPanel({ land, presets, onClose, onOpenSpot, onOpenField, onSheet }: {
  land: LandFeature; presets: Location[]; onClose: () => void; onOpenSpot: (lat: number, lon: number) => void; onOpenField: (id: string) => void; onSheet?: (px: number) => void;
}) {
  const p = land.properties;
  const [detail, setDetail] = useState<LandDetail | null>(null);
  const [spot, setSpot] = useState<Spot>({ state: 'loading' });
  const [tries, setTries] = useState(0);
  const [lon, lat] = p.centroid;
  useEffect(() => { onSheet?.(Math.round(window.innerHeight * 0.58)); }, [onSheet]);
  useEffect(() => { let ok = true; setDetail(null); api.getLand(p.id).then((d) => ok && setDetail(d)); return () => { ok = false; }; }, [p.id]);
  useEffect(() => {
    let ok = true;
    setSpot({ state: 'loading' });
    api.analyzeSpot(lat, lon).then((r) => {
      if (!ok) return;
      if (r.kind === 'ok') setSpot({ state: 'ok', loc: r.loc });
      else if (r.kind === 'preset') { const pre = presets.find((l) => l.id === r.id); setSpot(pre ? { state: 'ok', loc: pre } : { state: 'error', message: 'This land is inside one of the prepared fields.' }); }
      else setSpot({ state: 'error', message: r.message });
    });
    return () => { ok = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.id, tries]);
  const loc = spot.state === 'ok' ? spot.loc : api.spotPlaceholder(lat, lon);
  const bc = p.province === 'BC';
  return (
    <aside className="lpanel" aria-label={`${p.name}, ${kindLabel(p.kind).toLowerCase()}`} data-testid="land-panel">
      <div className="lp-grab" aria-hidden="true"><i /></div>
      <button className="icon-btn lp-close" onClick={onClose} aria-label="Close" title="Close" data-testid="land-close"><Icon name="close" size={20} /></button>
      <div className="lp-scroll" key={p.id}>
        <header className="lp-head">
          <p className="lp-eyebrow">Information for First Nations and tribal farmers and land managers</p>
          <span className={`lp-pill ${p.kind}`} data-testid="land-pill"><i />{kindLabel(p.kind)}</span>
          <h1 data-testid="land-name">{p.name}</h1>
          <p className="lp-nation"><b>{p.nation}</b>{bc ? ` · British Columbia${p.band_number ? ` · band ${p.band_number}` : ''}` : ' · California'}</p>
          <p className="lp-area">{areaText(p.area_ha)}</p>
        </header>

        <section className="lp-sec" aria-labelledby="lp-has">
          <h2 id="lp-has" className="fp-h">What this land has</h2>
          <p className="lp-note">From public satellite, soil and weather data at the middle of this land. It describes the ground here, not how anyone uses it.</p>
          {spot.state === 'loading' && <div className="wk-skel" aria-label="Loading">{[88, 70, 80, 60].map((w, i) => <span key={i} className="skel" style={{ width: `${w}%` }} />)}</div>}
          {spot.state === 'error' && <p className="gap-line">{spot.message} <button className="btn btn-outline btn-sm" onClick={() => setTries(tries + 1)}>Try again</button></p>}
          {spot.state === 'ok' && <Has loc={spot.loc} />}
        </section>

        <NationTools loc={loc} defaultOpen />

        <section className="lp-sec" aria-labelledby="lp-near">
          <h2 id="lp-near" className="fp-h">Nearby fields</h2>
          {!detail && <div className="wk-skel"><span className="skel" style={{ width: '80%' }} /></div>}
          {detail && !detail.nearby.length && <p className="lp-note">No prepared fields or catalogued farms within {detail.nearby_radius_km} km.</p>}
          {detail && detail.nearby.length > 0 && (
            <ul className="lp-near" data-testid="land-nearby">
              {detail.nearby.map((n) => (
                <li key={n.id}>
                  <button onClick={() => (n.kind === 'prepared field' ? onOpenField(n.id) : onOpenSpot(n.lat, n.lon))}>
                    <span><b>{n.name}</b><small>{n.kind === 'prepared field' ? 'Prepared field' : [n.crop, n.acres ? `${Math.round(n.acres)} acres` : null].filter(Boolean).join(' · ') || 'Farm'}</small></span>
                    <em>{(n.distance_km * 0.621).toFixed(1)} mi</em>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {detail?.website && (
          <p className="lp-web"><a href={detail.website} target="_blank" rel="noreferrer" data-testid="land-website"><Icon name="link" size={16} />{detail.nation} public website</a></p>
        )}
        <p className="lp-fine" data-testid="land-caveat">{detail?.caveat ?? 'Reserve, reservation and trust boundaries are legal or statistical lines, not traditional territory and not where a Nation’s rights apply.'} Nothing here implies that any Nation or tribe uses, endorses or partners with CropLytics.
          {detail?.source && <> Boundary source: <a href={detail.source.url} target="_blank" rel="noreferrer">{detail.source.title.split(',')[0]}</a>.</>}</p>
      </div>
    </aside>
  );
}

/** Crops, soil, water, weather: four short rows from the analysis at the land's centroid. */
function Has({ loc }: { loc: Location }) {
  const sp = loc.spot;
  const years = Object.keys(loc.crop_history ?? {}).map(Number).filter((y) => y >= 2016).sort((a, b) => b - a);
  const crops = years.slice(0, 6).map((y) => ({ y, c: cropName(loc.crop_history[y]) }));
  const soil = soilFacts(loc.soil);
  const w = loc.water;
  const waterBits = [w?.source === 'surface' ? 'Surface water' : w?.source === 'groundwater' || w?.source === 'wells' ? 'Wells' : null, known(w?.district) ? w.district : null, known(w?.sgma_subbasin) ? `Basin: ${w.sgma_subbasin}` : null, loc.water_context?.watershed ? `Watershed: ${loc.water_context.watershed}` : null].filter(Boolean);
  const farm = sp?.cropland !== false && crops.length > 0;
  return (
    <div className="lp-has" data-testid="land-has">
      <dl>
        <div><dt>Crop history</dt><dd>{farm ? crops.map((c) => <span key={c.y} className="lp-crop"><b>{c.y}</b> {c.c}</span>) : 'Satellite crop maps show little or no cropping here.'}</dd></div>
        <div><dt>Soil</dt><dd>{[soil.texture ? `${soil.texture}.` : null, soil.holds, soil.drains, soil.salt].filter(Boolean).join(' ') || 'No soil map for this spot.'}</dd></div>
        <div><dt>Water</dt><dd>{waterBits.length ? waterBits.join(' · ') : 'No water district or basin found for this spot.'}</dd></div>
      </dl>
      <ThisWeek loc={loc} compact />
    </div>
  );
}
