// The Nation panel: opens when a reserve or tribal land is clicked on the map or picked from the list.
// Name and Nation, what this land has (the tap-anywhere analysis at its centroid), the Nation tools, nearby fields, the Nation's
// own website where our data names one. Plain language, public data only; nothing here speaks for the Nation.
import { useEffect, useState } from 'react';
import * as api from '../../api';
import type { Location } from '../../types';
import Icon from '../Icons';
import { t, tx } from '../../i18n';
import { NationTools } from '../week/NationTools';
import { ThisWeek } from '../week/ThisWeek';
import { cropName, soilFacts, known } from '../ui/shared';
import { areaText, kindLabel, regionName, regionOf, type LandDetail, type LandFeature } from './lands';
import './lands.css';

type Spot = { state: 'loading' } | { state: 'ok'; loc: Location } | { state: 'error'; message: string };

/** Farmed blocks on these lands, outlined from public crop maps (DWR 2023 field outline) and saved as drawn fields. */
const FARMS: Record<string, { id: string; name: string; note: string }> = {
  'ca-r3265R': { id: 'my_eNpNVduKFFEM_JVhnhTScHJufXqf_QDxTZZ9GNaRFXSVFQUR_91UVXaVGbrPNalUKunf55_nm2rnx_PN-e3Tj8fr6fL44XT5_BH_08dP188f7PTux5fv11-nd5fH-4fr06fL6dX7r_cPl9Ob68P19dnO3843t7e3m9fqbXi1tvbex25bK7ZN26pbs-2oMcIM79jYY82H5h7zHhfctbabT86w2awui2GxYb6HKT9sWusxqsN2q81W-LRufcYjrhzx84Y1Qgivu3zDXQwPrWM2rAgOILSdiz32HagOTAH5gIFYcu30RL0CEZ460g5OwvHWHDFsgVshFauKLPYBpL2sM9wwy2G8wvQy4nFxIIMR3aC92hnCQdC04QaqeyNXCwwB-86TA4jDwwJJm-NZcM4BJG62zuxsDrDxmmkY4AEF63ExTNFVE0wHAXHWRRu3QLrMdNARl4l-J_pwOxV-ZYQRQBVzTFHYA2fMH3JAVMUSwCLZMAP_zpxhiCymTpTCFFFrYpInlAg8KykY4hYsxW5FtNrtXOqMohsTN2XKlTt_jh00TyFw3YqoKkQAxhtXhoAW6mM3IcpL8e8VUXlLW40qjj8ePC_U6cERS9wfWCHcgisFI9ho3F8kRGJi-palhgFowTQPUkkh1RGIpZNCzYS5CTxhtFIwMTRUCQwhsEzdAbPjX06qlJOC2bNyHC65OslkIno5F04XfEqeCLFbxuq4U0XfZJacIoVSWI3x7NRUUTVP1TbQoIc0z-Ka2qaMpN6U7VLKCoxzUhJ1E8AlErOOB4Penms-mxgaTbHsVQTHDKvQR-oLRrv6E7xV6tzZz0C8QFKQnaYEZ0lUA9pGwZTUckJ00U1WlOOwQPOHZWTKS-BM7QycdhWUrEHHK8QOC2wSBz2Eze4YMQNRh7LsxTJxIgSFiwPFOqsJHZO12551n1U-ScueTUZlphwcKilX7I08sRorpVNVHy7ZIBmBiPdlSlgrvgGU1iR_jHNrWVzM-vFfatWuyWjSqWZALdOwPjo4wnKPAfoPk1nYgefka0WTQ7cJJR7P3QZ1wnyw41WbjagbuGqKgxFmEwW_lWWlT0_Nb4nvd3d3f_4CplJ31g', name: 'Prune and alfalfa field', note: '53 ha, alfalfa 2019 to 2024 (public crop maps)' },
};

export function LandPanel({ land, presets, onClose, onOpenSpot, onOpenField, onOpenFarm, onSheet }: {
  land: LandFeature; presets: Location[]; onClose: () => void; onOpenSpot: (lat: number, lon: number) => void; onOpenField: (id: string) => void; onOpenFarm?: (id: string) => void; onSheet?: (px: number) => void;
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
      else if (r.kind === 'preset') { const pre = presets.find((l) => l.id === r.id); setSpot(pre ? { state: 'ok', loc: pre } : { state: 'error', message: t('lp.inPrepared') }); }
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
      <button className="icon-btn lp-close" onClick={onClose} aria-label={t('common.close')} title={t('common.close')} data-testid="land-close"><Icon name="close" size={20} /></button>
      <div className="lp-scroll" key={p.id}>
        <header className="lp-head">
          <p className="lp-eyebrow">{t('lp.eyebrow')}</p>
          <span className={`lp-pill ${p.kind}`} data-testid="land-pill"><i />{kindLabel(p.kind)}</span>
          <h1 data-testid="land-name">{p.name}</h1>
          <p className="lp-nation"><b>{p.nation}</b>{` · ${regionName(regionOf(p))}, ${p.country === 'CAN' ? t('merge2.canada') : t('merge2.us')}${bc && p.band_number ? t('merge2.bandN', { n: p.band_number }) : ''}`}</p>
          <p className="lp-area">{areaText(p.area_ha)}</p>
        </header>

        <section className="lp-sec" aria-labelledby="lp-has">
          <h2 id="lp-has" className="fp-h">{t('lp.has')}</h2>
          <p className="lp-note">{t('lp.hasNote')}</p>
          {spot.state === 'loading' && <div className="wk-skel" aria-label={t('lp.loading')}>{[88, 70, 80, 60].map((w, i) => <span key={i} className="skel" style={{ width: `${w}%` }} />)}</div>}
          {spot.state === 'error' && <p className="gap-line">{spot.message} <button className="btn btn-outline btn-sm" onClick={() => setTries(tries + 1)}>{t('lp.retry')}</button></p>}
          {spot.state === 'ok' && <Has loc={spot.loc} />}
        </section>

        <NationTools loc={loc} defaultOpen />

        {FARMS[p.id] && onOpenFarm && (
          <section className="lp-sec" aria-labelledby="lp-farm">
            <h2 id="lp-farm" className="fp-h">{t('lp.farm')}</h2>
            <ul className="lp-near" data-testid="land-farm">
              <li><button onClick={() => onOpenFarm(FARMS[p.id].id)}><span><b>{tx(FARMS[p.id].name)}</b><small>{tx(FARMS[p.id].note)}</small></span></button></li>
            </ul>
          </section>
        )}

        <section className="lp-sec" aria-labelledby="lp-near">
          <h2 id="lp-near" className="fp-h">{t('lp.near')}</h2>
          {!detail && <div className="wk-skel"><span className="skel" style={{ width: '80%' }} /></div>}
          {detail && !detail.nearby.length && <p className="lp-note">{t('lp.noNear', { n: detail.nearby_radius_km })}</p>}
          {detail && detail.nearby.length > 0 && (
            <ul className="lp-near" data-testid="land-nearby">
              {detail.nearby.map((n) => (
                <li key={n.id}>
                  <button onClick={() => (n.kind === 'prepared field' ? onOpenField(n.id) : onOpenSpot(n.lat, n.lon))}>
                    <span><b>{n.name}</b><small>{n.kind === 'prepared field' ? t('lp.prepared') : [n.crop, n.acres ? t('lp.acres', { n: Math.round(n.acres) }) : null].filter(Boolean).join(' · ') || t('lp.farmw')}</small></span>
                    <em>{(n.distance_km * 0.621).toFixed(1)} mi</em>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {detail?.website && (
          <p className="lp-web"><a href={detail.website} target="_blank" rel="noreferrer" data-testid="land-website"><Icon name="link" size={16} />{t('lp.web', { nation: detail.nation })}</a></p>
        )}
        <p className="lp-fine" data-testid="land-caveat">{detail?.caveat ?? t('lp.caveat')} {t('lp.nothing')}
          {detail?.source && <> {t('lp.source')} <a href={detail.source.url} target="_blank" rel="noreferrer">{detail.source.title.split(',')[0]}</a>.</>}</p>
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
  const waterBits = [w?.source === 'surface' ? t('lp.surface') : w?.source === 'groundwater' || w?.source === 'wells' ? t('lp.wells') : null, known(w?.district) ? w.district : null, known(w?.sgma_subbasin) ? t('lp.basin', { v: String(w.sgma_subbasin) }) : null, loc.water_context?.watershed ? t('lp.watershed', { v: String(loc.water_context.watershed) }) : null].filter(Boolean);
  const farm = sp?.cropland !== false && crops.length > 0;
  return (
    <div className="lp-has" data-testid="land-has">
      <dl>
        <div><dt>{t('lp.crops')}</dt><dd>{farm ? crops.map((c) => <span key={c.y} className="lp-crop"><b>{c.y}</b> {c.c}</span>) : t('lp.noCrops')}</dd></div>
        <div><dt>{t('lp.soil')}</dt><dd>{[soil.texture ? `${soil.texture}.` : null, soil.holds, soil.drains, soil.salt].filter(Boolean).join(' ') || t('lp.noSoil')}</dd></div>
        <div><dt>{t('lp.water')}</dt><dd>{waterBits.length ? waterBits.join(' · ') : t('lp.noWater')}</dd></div>
      </dl>
      <ThisWeek loc={loc} compact />
    </div>
  );
}
