// One farmer-first field panel. Order: what this field is -> "Your field now" answers -> next steps -> More detail (about the
// ground, last 3 seasons, sources). A floating paper card on a desktop (the field name collapses into a sticky one-line bar
// on scroll; the one primary action sits in the footer); a draggable bottom sheet on a phone (peek, half, full).
import { DisabilityHelp } from '../help/DisabilityHelp';
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import { bcGap, isBC, type Extras, type ISSPhoto, type NasaNow, type ProvMap, type RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import { ISSFigure, NasaList } from './NasaSection';
import { SourcesSheet } from './Sources';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { useEffect, useRef, useState } from 'react';
import { AboutField, StepLine, Workflow, CROP_COL, rotName, waterGap, EventLog, acres, coords, county, cropKey, fieldName, latestCrop, place, stateFieldNo, type Step } from './shared';
import { t, locale } from '../../i18n';
import { ThisWeek } from '../week/ThisWeek';
import { DescribeField } from '../a11y/DescribeField';
import { Answer, KeyFacts, LimitControl, StepShell, useSheet, type Tone } from './StepShell';
import { useDetail } from './Detail';
import { FirstNationsCard } from './FirstNations';
import { SalmonPanel } from '../salmon/SalmonPanel';
import { NationChip, NationTools, ReservePill } from '../week/NationTools';
import { LandsList } from '../lands/LandsList';
import type { LandFeature } from '../lands/lands';
import { CatalogGroup } from '../week/CatalogGroup';
import type { Catalog, CatalogItem } from '../week/catalog';
import { FieldNow, LastSeasons, latestClearT, rainNow, stage, whenT, type LoadState } from './FieldNow';
import { MONTHS, TODAY_T, isRainFed, latestAt, mmToAfac } from '../../lib';
import { MineFacts, MineHead, MineNotices, MyFieldsGroup, type MineAction } from '../draw/MyFieldBits';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; daily: Daily | null;
  nasa: NasaDataset[] | null; nasaNow: NasaNow | null; extras: Extras; iss: { photo: ISSPhoto; credit: string } | null; dataState: LoadState; dailyState: LoadState;
  t: number; setT: (t: number) => void; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
  /** phone: how much of the sheet shows above the tab bar, so the map keeps the field in view */
  onSheet?: (visiblePx: number) => void;
  /** back to step 1 */
  onBack?: () => void;
  /** set the grower's water limit (acre-ft/acre) */
  setAllocation?: (v: number) => void;
  /** set the grower's current rotation (null: back to the one the satellites show) */
  onToday?: (strategyId: string | null) => void;
  /** a tapped spot whose analysis failed: try again */
  onSpotRetry?: () => void;
  /** a field the user drew: Rename, Redraw (also "Fix the outline") and Delete */
  onMine?: (a: MineAction) => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const thumbs = useThumbs();
  const detail = useDetail();
  const [src, setSrc] = useState(false);
  const [rotOpen, setRotOpen] = useState(false);
  useEffect(() => { setSrc(false); setRotOpen(false); }, [loc.id]);
  const now = latestCrop(loc);
  const sp = loc.spot;
  const isToday = p.t === TODAY_T;
  const crop = now.key;
  const loading = sp?.state === 'loading';
  const fieldLine = <><b>{fieldName(loc)}</b> · {t('ui.n_acres', { n: acres(loc) })}{now.year != null && Number.isFinite(now.year) ? <> · <span className="nw"><i className="crop-sw" style={{ background: CROP_COL(crop) }} />{t('ui.crop_in', { crop: now.crop.toLowerCase(), year: now.year })}</span></> : null}</>;
  const facts = nowFacts(p);
  return (
    <StepShell id="now" testid="field-panel" resetKey={loc.id} onSheet={p.onSheet} onClose={p.onClose} onBack={p.onBack}
      field={fieldLine}
      title={isToday ? t('ui.fp.title') : t('ui.fp.title_then', { when: whenT(p.t) })}
      top={<>
        {loc.mine ? <MineHead loc={loc} onAction={(a) => p.onMine?.(a)} /> : sp && <p className="spot-label" data-testid="spot-label"><i className={`live-dot ${sp.state}`} />{t('ui.fp.spot')}</p>}
        {!loc.mine && (isBC(loc) || sp) && <ReservePill loc={loc} />}
        {loading && <p className="spot-progress" role="status" data-testid="spot-progress">{t('ui.fp.reading')}</p>}
        {loc.mine && <MineNotices loc={loc} onRetry={p.onSpotRetry} onFix={() => p.onMine?.('redraw')} />}
        {sp?.state === 'error' && !loc.mine && <div className="notice spot-notice" role="alert" data-testid="spot-error"><span>{sp.error}</span>{p.onSpotRetry && <button className="btn btn-outline btn-sm" onClick={p.onSpotRetry}>{t('ui.retry')}</button>}</div>}
        {sp?.state === 'ready' && sp.cropland === false && <div className="notice spot-notice" data-testid="spot-not-farm"><b>{t('ui.fp.nofarm')}</b> {t('ui.fp.nofarm_t', { map: loc.region === 'bc' ? t('ui.fp.map_bc') : t('ui.fp.map_ca') })}</div>}
      </>}
      answer={<>{isToday ? <WaterAnswer strategies={p.strategies} allocation={p.allocation} exampleLimit={p.exampleLimit} state={p.dataState} /> : <Answer headline={facts.stage ?? t('ui.loading')} sub={t('ui.fp.pickToday')} loading={!facts.stage && p.dataState === 'loading'} />}<NationChip loc={loc} openDetail={() => detail.set(true)} />{!loading && <DescribeField loc={loc} />}</>}
      detailWhat={t('ui.fp.detailWhat')}
      detail={<>
        <h2 className="fp-h">{isToday ? t('ui.fp.numbers') : t('ui.fp.title_then', { when: whenT(p.t) })}</h2>
        <p className="fp-id">{loc.mine ? t('ui.fp.drawn') : sp ? (sp.fallbackSquare || sp.state !== 'ready' ? t('ui.fp.square') : loc.dwr_id ? `${t('ui.statefield')} ${loc.dwr_id}` : t('ui.fp.outline')) : isBC(loc) ? t('ui.place.bc') : stateFieldNo(loc)}, {coords(loc)} · {place(loc)}</p>
        <FieldNow dataState={p.dataState} dailyState={p.dailyState} thumb={thumbs?.[loc.id] ?? null} extras={p.extras} nasaNow={p.nasaNow} loc={loc} cal={p.cal} regional={p.regional} regionalLive={p.regionalLive} strategies={p.strategies} allocation={p.allocation} exampleLimit={p.exampleLimit} t={p.t} daily={p.daily} prov={p.prov} />
        {loc.mine && <MineFacts loc={loc} />}
        {isBC(loc) && !loc.mine && <FirstNationsCard loc={loc} />}
        {isBC(loc) && !loc.mine && <SalmonPanel locId={loc.id} />}
        {!loc.mine && <NationTools loc={loc} />}
        <DisabilityHelp region={loc.region} />
        {!sp && <button className="btn btn-text" onClick={() => p.onStep('year')} data-testid="step-year"><Icon name="cube" />{t('ui.fp.yearmap')}</button>}
        <h2 className="fp-h" data-testid="nasa-section">{t('ui.fp.nasa')}</h2>
        <ISSFigure iss={p.iss} />
        {p.nasa ? <NasaList list={p.nasa} /> : <p className="muted">{t('ui.loading')}</p>}
        <h2 className="fp-h">{t('ui.fp.ground')}<button className="btn btn-text btn-sm" onClick={() => p.onStep('drill')} data-testid="step-drill"><Icon name="cube" />{t('ui.fp.under')}</button></h2>
        <AboutField loc={loc} prov={p.prov} cal={p.cal} insurance={p.extras.insurance ?? loc.rma ?? null} insGap={bcGap(loc, 'insurance')} />
        {!sp && <><h2 className="fp-h">{t('ui.fp.last3')}</h2><LastSeasons loc={loc} cal={p.cal} t={p.t} /></>}
        {p.events.length > 0 && <><h2 className="fp-h">{t('ui.fp.happened')}</h2><p className="fp-sub">{t('ui.fp.clickone')}</p><EventLog events={p.events} setT={p.setT} /></>}
        <button className="btn btn-text sources-link" onClick={() => setSrc(true)} data-testid="sources-link">{t('ui.src.title')}</button>
      </>}
      next={{ label: t('ui.fp.next'), sub: t('ui.fp.next_s'), onClick: () => p.onStep('season'), testid: 'now-to-season' }}
      after={<>
        <p className="footnote">{t('ui.fp.footnote')}</p>
        {src && <SourcesSheet bc={isBC(loc)} onClose={() => setSrc(false)} />}
      </>}>
      <ThisWeek loc={loc} compact />
      {isToday && p.allocation != null && p.setAllocation && p.strategies?.some((x) => x.is_baseline && !isRainFed(x)) && <LimitControl value={p.allocation} example={p.exampleLimit} onChange={p.setAllocation} />}
      <KeyFacts facts={loading ? [] : [
        { label: t('ui.fp.rotnow'), value: facts.rotation ? <>{facts.rotation}<small className="rot-src">{facts.picked ? t('ui.fp.yourchoice') : t('ui.fp.fromsat')}{p.onToday && <> · <button type="button" className="link-btn" onClick={() => setRotOpen(!rotOpen)} aria-expanded={rotOpen} data-testid="change-rotation">{rotOpen ? t('ui.close') : t('ui.change')}</button></>}</small></> : pend(p.dataState) },
        { label: t('ui.fp.growing'), value: facts.stage ?? pend(p.dataState) },
        { label: t('ui.rain1oct'), value: facts.rain ?? pend(p.dailyState), tone: facts.rainTone },
        { label: t('ui.gw'), value: facts.gw ?? pend(p.dataState), tone: facts.gwTone },
      ]} />
      {rotOpen && p.strategies && p.onToday && <RotationPicker strategies={p.strategies} onPick={(id) => { p.onToday!(id); setRotOpen(false); }} />}
    </StepShell>
  );
}

/** "What do you grow now?": every rotation on this field; the satellite-detected one is marked and is the way back. */
function RotationPicker({ strategies, onPick }: { strategies: RotationStrategy[]; onPick: (id: string | null) => void }) {
  const cur = strategies.find((s) => s.is_baseline);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, []);
  return (
    <div className="rot-pick" ref={ref} data-testid="rotation-picker">
      <p className="rot-q">{t('ui.rp.q')}</p>
      <div className="opt-list" role="radiogroup" aria-label={t('ui.rp.aria')}>
        {[...strategies].sort((a, b) => Number(!!b.detected) - Number(!!a.detected)).map((s) => (
          <button key={s.id} type="button" role="radio" aria-checked={s.id === cur?.id} className={`opt-row ${s.id === cur?.id ? 'on' : ''}`} onClick={() => onPick(s.detected ? null : s.id)} data-testid={`today-${s.id}`}>
            <span className="opt-radio" aria-hidden="true" />
            <span className="opt-body"><b>{s.short_name.replace(/\s*\(current\)$/i, '')}</b>{s.detected && <small>{t('ui.rp.sat')}</small>}</span>
            <span className="opt-fit"><b>{isRainFed(s) ? t('ui.rainfed') : mmToAfac(s.water.irrigation_need_mm.value).toFixed(1)}</b><small>{isRainFed(s) ? '' : t('ui.u.afac')}</small></span>
          </button>
        ))}
      </div>
      <p className="step-note">{t('ui.rp.note')}</p>
    </div>
  );
}

const pend = (s: LoadState) => (s === 'timeout' ? <span className="na">{t('ui.na_now')}</span> : <span className="skel" aria-hidden="true" />);
const bandOf = (v: number, hi: string, mid: string, lo: string) => (v >= 67 ? hi : v > 33 ? mid : lo);
/** Step 2's three facts in the grower's words, for the viewing date. */
function nowFacts(p: FieldPanelProps) {
  const cal = p.cal;
  const dt = cal ? latestClearT(cal, p.t) : null;
  const stageText = cal && dt != null ? stage(cal, dt).text : null;
  const rain = rainNow(p.nasaNow, p.daily, p.t);
  const gr = p.regional ? latestAt(p.regional.grace_gw_pct.values, p.t) : null;
  const base = p.strategies?.find((x) => x.is_baseline);
  return {
    rotation: base ? base.short_name.replace(/\s*\(current\)$/i, '') : null,
    picked: !!base && base.detected === false,
    stage: stageText,
    rain: rain ? <>{rain.inches.toFixed(1)} in <small>{t('ui.pct_normal', { n: Math.round(rain.pct ?? 0) })}</small></> : null,
    rainTone: (rain && (rain.pct ?? 100) < 85 ? 'warn' : undefined) as Tone | undefined,
    gw: gr ? <>{bandOf(gr.v, t('ui.fp.above'), t('ui.fp.about'), t('ui.fp.below'))} <small>{t('ui.fp.basin')}</small></> : null,
    gwTone: (gr && gr.v <= 33 ? 'warn' : undefined) as Tone | undefined,
  };
}

/** Step 2's answer: will today's rotation fit the water limit? */
function WaterAnswer({ strategies, allocation, exampleLimit, state }: { strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; state: LoadState }) {
  const base = strategies?.find((s) => s.is_baseline);
  if (!base) return state === 'timeout' ? <Answer headline={t('ui.wa.na')} /> : <Answer headline="" loading />;
  const need = mmToAfac(base.water.irrigation_need_mm.value);
  const rf = isRainFed(base), g = allocation != null ? waterGap(need, allocation) : null, short = !rf && !!g?.short, even = !rf && !!g?.even;
  const lim = allocation != null ? `${allocation.toFixed(1)}${exampleLimit ? ` ${t('ui.wa.example')}` : ''}` : '';
  const hl = rf ? t('ui.wa.rainfed') : allocation == null ? t('ui.wa.needs', { n: need.toFixed(1) }) : short ? t('ui.wa.short', { n: g!.by }) : even ? t('ui.wa.even') : t('ui.wa.yes');
  const sb = !rf && allocation != null ? t('ui.wa.sub', { rot: rotName(base), n: need.toFixed(1), lim }) : t('ui.wa.sub_rf', { rot: rotName(base) });
  return <Answer speak={`${hl} ${sb}`} tone={short ? 'warn' : even || allocation == null ? 'neutral' : 'good'} headline={hl} sub={sb} />;
}

/** "Pick your field": one paper surface, one row per field with a satellite thumbnail (outline drawn), a 2023-2026 season strip,
 *  one line of facts in grower units and one line of what is notable. A BC field the API serves sits under its own
 *  "British Columbia" heading (and chip); without one, BC is a quiet "not set up yet" row at the bottom. */
/** Torres-Martinez Reservation farm field (check_api): opens Nation tools with tribal land status. */
export const NATION_EXAMPLE = { lat: 33.51, lon: -116.12, label: t('ui.nx.label'), sub: t('ui.nx.sub') };
export function FieldPicker(p: { mine?: Location[]; onDraw?: () => void; locations: Location[]; live: boolean | null; strips: Record<string, Record<number, string>>; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void; catalog?: Catalog | null; catGroup?: string | null; setCatGroup?: (g: string | null) => void; onCatalogPick?: (it: CatalogItem) => void; onExample?: () => void; onExampleBC?: () => void; onNationsExample?: () => void; onNationExample?: () => void; onSheet?: (visiblePx: number) => void ; lands?: LandFeature[] | null; activeLandId?: string | null; onPickLand?: (id: string) => void; tab?: 'fields' | 'lands'; setTab?: (t: 'fields' | 'lands') => void }) {
  const sheet = useSheet(p.onSheet, { initial: 'peek', peek: () => Math.round(window.innerHeight * 0.35) });
  const thumbs = useThumbs();
  const [q, setQ] = useState('');
  const [fam, setFam] = useState<string | null>(null);
  const nBC = p.locations.filter(isBC).length;
  const fams = [...(['rice', 'forage'] as const).map((f) => ({ f: f as string, label: f === 'rice' ? t('ui.pk.rice') : t('ui.pk.forage'), n: p.locations.filter((l) => familyOf(l) === f).length })), { f: 'bc', label: t('ui.place.bc'), n: nBC }].filter((x) => x.n > 0);
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const hit = (l: Location) => (!fam || (fam === 'bc' ? isBC(l) : familyOf(l) === fam)) && words.every((w) => `${fieldName(l)} ${county(l)} ${isBC(l) ? 'british columbia bc' : 'county california'} ${latestCrop(l).crop} ${l.water?.district ?? ''}`.toLowerCase().includes(w));
  const shownCA = p.locations.filter((l) => !isBC(l) && hit(l)), shownBC = p.locations.filter((l) => isBC(l) && hit(l));
  const shown = [...shownCA, ...shownBC];
  return (
    <aside ref={sheet.ref} id="field-panel" tabIndex={-1} className={`picker2 pick-sheet sheet-${sheet.snap}`} data-testid="fields-panel" aria-label={t('ui.flow.pick.label')} {...sheet.handlers}>
      <button className="fp-grab" onClick={sheet.cycle} onKeyDown={sheet.onKey} aria-label={t('ui.resize')} data-testid="grab"><i /></button>
      <div className="pk-scroll">
      <header className="pk-head">
        <h1>{t('ui.flow.pick.label')}</h1>
        {p.onClose && <button className="icon-btn" onClick={p.onClose} title={t('ui.close')} aria-label={t('ui.close')}><Icon name="close" size={20} /></button>}
      </header>
      {p.onPickLand && p.setTab && (
        <div className="pk-tabs" role="tablist" aria-label={t('ui.pk.whattopick')}>
          {([['fields', t('ui.pk.fields')], ['lands', t('ui.pk.lands')]] as const).map(([k, label]) => (
            <button key={k} role="tab" aria-selected={p.tab === k} className={p.tab === k ? 'on' : ''} onClick={() => p.setTab!(k)} data-testid={`pick-tab-${k}`}>{label}{k === 'lands' && p.lands ? <small>{p.lands.length.toLocaleString(locale)}</small> : null}</button>
          ))}
        </div>
      )}
      {p.tab === 'lands' && p.onPickLand ? <LandsList lands={p.lands ?? null} activeId={p.activeLandId ?? null} onPick={p.onPickLand} /> : <>
      <StepLine id="pick" purpose={t('ui.pk.purpose')} />
      {p.onExample && p.locations.some((l) => l.id === 'car_colusa_rice') && (
        <div className="nx-card ex-card" data-testid="example-card">
          <img className="ex-thumb" src={`${import.meta.env.BASE_URL}thumbs/car_colusa_rice.jpg`} alt="" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <div className="ex-body">
            <h2>{t('ui.pk.ex_h')}</h2>
            <p>{t('ui.pk.ex_p')}</p>
            <button className="btn btn-primary" onClick={p.onExample} data-testid="example-open">{t('ui.pk.open')}</button>
          </div>
        </div>
      )}
      {p.onExampleBC && p.locations.some((l) => l.id === 'bc_salmon_river_forage') && (
        <div className="nx-card ex-card" data-testid="example-card-bc">
          <img className="ex-thumb" src={`${import.meta.env.BASE_URL}thumbs/bc_salmon_river_forage.jpg`} alt="" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <div className="ex-body">
            <h2>{t('bcex.card.h')}</h2>
            <p>{t('bcex.card.p')}</p>
            <button className="btn btn-primary" onClick={p.onExampleBC} data-testid="example-open-bc">{t('ui.pk.open')}</button>
          </div>
        </div>
      )}
      {p.onNationsExample && p.locations.some(isBC) && (
        <div className="nx-card ex-card" data-testid="nations-example-card">
          <img className="ex-thumb" src={`${import.meta.env.BASE_URL}thumbs/bc_salmon_river_forage.jpg`} alt="" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <div className="ex-body">
            <h2>{t('ui.pk.nx_h')}</h2>
            <p>{t('ui.pk.nx_p')}</p>
            <button className="btn btn-primary" onClick={p.onNationsExample} data-testid="nations-example">{t('ui.pk.open')}</button>
          </div>
        </div>
      )}
      {p.locations.length > 1 && (
        <div className="pk-filter">
          <label className="pk-search"><Icon name="search" size={16} /><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('ui.pk.search')} aria-label={t('ui.pk.search_aria')} data-testid="pk-search" /></label>
          <div className="chips" role="group" aria-label={t('ui.pk.crop')}>
            {fams.map(({ f, label, n }) => <button key={f} className="chip" aria-pressed={fam === f} onClick={() => setFam(fam === f ? null : f)} data-testid={`chip-${f}`}><Icon name="check" size={16} className="check" />{label} <span className="n">{n}</span></button>)}
          </div>
        </div>
      )}
      {p.live === false && <p className="notice offline-note" data-testid="offline-note">{t('ui.pk.offline')}</p>}
      {p.locations.length === 0 && <p className="loading-note">{t('ui.pk.loading')}</p>}
      {([['ca', shownCA], ['bc', shownBC]] as const).map(([rg, rows]) => rows.length > 0 && (
      <div key={rg}>
      {rg === 'bc' && <h2 className="pk-group" data-testid="pk-group-bc">{t('ui.place.bc')}</h2>}
      <ul className="pk-list" data-testid={rg === 'bc' ? 'field-table-bc' : 'field-table'}>
        {rows.map((l) => {
          const now = latestCrop(l), th = thumbs?.[l.id], strip = p.strips[l.id];
          return (
            <li key={l.id}>
              <button className={`pk-row ${p.selectedId === l.id ? 'on' : ''}`} aria-current={p.selectedId === l.id ? 'true' : undefined} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
                <span className="pk-thumb">
                  <img src={`${import.meta.env.BASE_URL}thumbs/${l.id}.jpg`} alt={t('ui.pk.satview', { name: fieldName(l) })} onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }} />
                  {th && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={outlinePts(l, th.bbox)} /></svg>}
                </span>
                <span className="pk-body">
                  <b>{fieldName(l)}</b>
                  <span className="pk-facts">{place(l)} · {t('ui.n_acres', { n: acres(l) })} · {t('ui.crop_in', { crop: now.crop.toLowerCase(), year: now.year })}</span>
                  <span className="pk-note">{notable(l)}</span>
                  <span className="pk-strip" title={t('ui.pk.strip')}>
                    {[2023, 2024, 2025, 2026].map((y) => <span key={y}><i>{(strip?.[y] ?? 'u'.repeat(36)).split('').map((c, k) => <em key={k} className={`c-${c}`} />)}</i><small>{y}</small></span>)}
                  </span>
                  <span className="pk-go">{p.selectedId === l.id ? t('ui.pk.continue') : t('ui.pk.pick')}<Icon name="right" size={16} /></span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      </div>
      ))}
      {p.locations.length > 0 && !shown.length && <p className="loading-note">{t('ui.pk.nomatch')} <button className="btn btn-outline btn-sm" onClick={() => { setQ(''); setFam(null); }}>{t('ui.pk.showall')}</button></p>}
      {p.catalog && p.onCatalogPick && p.setCatGroup && <CatalogGroup catalog={p.catalog} group={p.catGroup ?? null} setGroup={p.setCatGroup} onPick={p.onCatalogPick} />}
      {p.locations.length > 0 && !nBC && <button className="pk-bc" onClick={p.onBC}>{t('ui.pk.bc_not')} <u>{t('ui.pk.seewhy')}</u></button>}
      {p.onDraw && <MyFieldsGroup locs={p.mine ?? []} selectedId={p.selectedId} onSelect={p.onSelect} onDraw={p.onDraw} />}
      {p.onNationExample && (
        <button className="pk-bc" onClick={p.onNationExample} data-testid="nation-example">
          {NATION_EXAMPLE.label}: {NATION_EXAMPLE.sub}. <u>{t('ui.open')}</u>
        </button>
      )}
      <footer className="pk-foot"><button className="link" onClick={() => window.dispatchEvent(new CustomEvent('croplytics:about'))} data-testid="footer-a11y">{t('ui.a11y')}</button></footer>
      <details className="pk-more" data-testid="pk-more">
        <summary>{t('ui.pk.how')} <small>{t('ui.pk.optional')}</small></summary>
        <Workflow />
      </details>
      </>}
      </div>
    </aside>
  );
}
/** Crop family: from the API, else from the field id (car_ rice, caf_ forage). */
const familyOf = (l: Location) => l.family ?? (l.id.startsWith('car') ? 'rice' : l.id.startsWith('caf') ? 'forage' : 'other');
/** Field outline in thumbnail coordinates (360 x 240, plate carrée over a small box). */
function outlinePts(l: Location, b: number[]) {
  return l.geometry.coordinates[0].map(([x, y]) => `${(((x - b[0]) / (b[2] - b[0])) * 360).toFixed(1)},${(((b[3] - y) / (b[3] - b[1])) * 240).toFixed(1)}`).join(' ');
}
/** One line of what is notable about the field, from its record. */
function notable(l: Location) {
  const notes: string[] = [];
  // BC: the irrigation order is what is notable (no California water district)
  const order = l.water_context?.orders?.[0];
  if (l.region === 'bc') return order ? t('ui.nt.order', { month: MONTHS[+order.date.slice(5, 7) - 1], year: order.date.slice(0, 4) }) : '';
  const fallow = Object.entries(l.crop_history).filter(([y, c]) => +y >= 2016 && cropKey(c) === 'Left fallow').map(([y]) => +y);
  if (fallow.includes(2022)) notes.push(t('ui.nt.fallow22'));
  else if (fallow.length) notes.push(t('ui.nt.fallow', { year: fallow[fallow.length - 1] }));
  if (l.water?.source === 'surface') notes.push(l.water_real && l.water.district ? t('ui.nt.surface_d', { d: l.water.district }) : t('ui.nt.surface'));
  else if (l.water?.source) notes.push(/probation/i.test(l.water.sgma_status?.text ?? '') ? t('ui.nt.wells_prob') : t('ui.nt.wells'));
  const s = notes.join('; ');
  return s ? s.charAt(0).toUpperCase() + s.slice(1) + '.' : '';
}

let thumbsP: Promise<Record<string, { bbox: number[] }>> | null = null;
/** Satellite thumbnails of each field (public/thumbs), with the bounds needed to draw the outline. */
function useThumbs() {
  const [t, setT] = useState<Record<string, { bbox: number[] }> | null>(null);
  useEffect(() => { (thumbsP ??= fetch(`${import.meta.env.BASE_URL}thumbs/thumbs.json`).then((r) => r.json()).then((j) => j.fields).catch(() => ({}))).then(setT); }, []);
  return t;
}
