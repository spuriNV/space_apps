import { useEffect, useState } from 'react';
// "Coming season": outlooks for this winter and next season, always labelled as outlooks, not forecasts.
import { t, locale } from '../../i18n';
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import { linkOf } from '../../types';
import { bcGap, getRainAt, isBC, type RainAt, type NasaNow, type Outlook, type OutlookCat, type ProvMap, type RegionalLive } from '../../api';
import { whenT } from '../ui/FieldNow';
import type { Daily } from '../../season';
import { bareWindow } from '../../season';
import { RAIN_FED, TODAY_T, fmtDate, isRainFed, latestAt, mmToAfac, ordinal } from '../../lib';
const band = (v: number, hi: string, mid: string, lo: string) => (v >= 67 ? hi : v > 33 ? mid : lo);
import { GapLine, Src, acres, fieldName, place, rotName, stationsName, waterGap } from '../ui/shared';
import { Answer, KeyFacts, StepShell } from '../ui/StepShell';
import { What } from '../ui/What';
import { BARE_DEF } from '../../bare';

const SEASON: Record<string, string> = { OND: t('season.OND'), NDJ: t('season.NDJ'), DJF: t('season.DJF'), JFM: t('season.JFM'), FMA: t('season.FMA'), MAM: t('season.MAM'), AMJ: t('season.AMJ') };
const lean = (c: OutlookCat | null, kind: 'rain' | 'temp') => {
  if (!c || c.category.startsWith('equal')) return { words: t('season.noLean'), tilt: 0 };
  const up = c.category.startsWith('above'), weak = (c.prob ?? 40) <= 35;
  const w = kind === 'rain' ? (up ? t('season.wetter') : t('season.drier')) : (up ? t('season.warmer') : t('season.cooler'));
  return { words: t(weak ? 'season.barelyLeans' : 'season.leans', { w }), tilt: weak ? 0 : up ? 1 : -1 };
};
const DROUGHT: Record<string, string> = { No_Drought: t('season.dNone'), Persists: t('season.dPersists'), Improvement: t('season.dEase'), Removal: t('season.dEnd'), Development: t('season.dDevelop') };
const maf = (af: number) => (af >= 1e6 ? t('season.mafM', { n: (af / 1e6).toFixed(2) }) : t('season.mafK', { n: Math.round(af / 1000).toLocaleString(locale) }));
const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
const words = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export default function ComingSeason(p: { nasaNow: NasaNow | null; regional: Regional | null; regionalLive: RegionalLive; loc: Location; outlook: Outlook | null; cal: Calendar | null; daily: Daily | null; strategies: RotationStrategy[]; allocation: number; exampleLimit: boolean; prov: ProvMap; onCompare: () => void; onClose: () => void; onBack: () => void; onSheet?: (px: number) => void }) {
  const o = p.outlook;
  const soil = p.regional ? latestAt(p.regional.smap_rootzone_pct.values, TODAY_T, 14) : null, gw = p.regional ? latestAt(p.regional.grace_gw_pct.values, TODAY_T, 14) : null;
  const rainLean = o?.seasons.slice(0, 4).map((s) => lean(s.rain, 'rain').tilt) ?? [];
  const wetLean = rainLean.filter((x) => x > 0).length, dryLean = rainLean.filter((x) => x < 0).length;
  const surface = p.loc.water.source === 'surface';
  const shasta = o?.reservoirs.find((r) => /shasta/i.test(r.name)) ?? o?.reservoirs[0];
  const notReady = !!o?.notReady;
  // BC: no NOAA outlooks, CDEC reservoirs or allocations; the watershed and its irrigation orders instead
  const bc = isBC(p.loc), gOut = bcGap(p.loc, 'outlook'), wc = p.loc.water_context;
  const lastOrder = wc?.orders?.[wc.orders.length - 1];
  const freeform = !!(p.loc.spot || p.loc.mine);
  const gapWords = gOut ? t('season.gapBC') : freeform ? t('season.gapFree') : t('season.gapNotReady');
  const supply = bc ? `${wc?.watershed.split(';')[0] ?? t('season.noWatershed')}.${lastOrder ? ` ${t('season.lastOrder', { date: fmtDate(lastOrder.date) })}` : ''}`
    : !o ? t('season.loading') : notReady && surface ? (freeform ? t('season.resFree') : t('season.notReadyDot')) : surface
    ? `${shasta && shasta.pctAvg != null ? t('season.pctAvg', { name: words(shasta.name), n: Math.round(shasta.pctAvg) }) : ''}${o.cvpNow?.settlement != null ? ` ${t('season.yourAlloc', { n: o.cvpNow.settlement })}` : ''}`
    : gw ? t('season.basinGw', { w: band(gw.v, t('season.aboveUsual'), t('season.aboutUsual'), t('season.belowUsual')) }) : freeform && notReady ? t('season.basinFree') : t('season.gwNA');
  const today = p.strategies.find((s) => s.is_baseline);
  const nxt = today ? o?.irrigation?.[today.id]?.value ?? mmToAfac(today.water.irrigation_need_mm.value) : null;
  const nextNeed = nxt == null ? (p.strategies.length ? t('season.needNA') : t('season.loading')) : today && isRainFed(today) ? `${RAIN_FED}. ${t('season.fitsAny')}` : `${t('season.needsLimit', { n: nxt.toFixed(1), a: p.allocation.toFixed(1), ex: p.exampleLimit ? t('season.exampleP') : '' })} ${waterGap(nxt, p.allocation).short ? t('season.byShort', { by: waterGap(nxt, p.allocation).by }) : waterGap(nxt, p.allocation).even ? t('season.aboutEven') : t('season.itFits')}`;
  const bw = p.cal ? bareWindow(p.cal, p.daily, (p.cal.years ?? []).map((y) => y.year).filter((y) => y >= 2016 && y <= 2025)) : null;
  const allYearsBw = bw;
  const rainFed = !!today && isRainFed(today);
  const g = nxt != null ? waterGap(nxt, p.allocation) : null;
  const short = !rainFed && !!g?.short, even = !rainFed && !!g?.even;
  // NOAA rain forecast at the field, next 7 days (app/rain reads NOAA's full-detail shapes for the point)
  const [rain7, setRain7] = useState<{ id: string; r: RainAt | null } | null>(null);
  useEffect(() => { let ok = true; getRainAt(p.loc.centroid.lat, p.loc.centroid.lon, 7).then((r) => ok && setRain7({ id: p.loc.id, r })); return () => { ok = false; }; }, [p.loc.id, p.loc.centroid.lat, p.loc.centroid.lon]);
  const r7 = rain7?.id === p.loc.id ? rain7.r : undefined;
  const rainWords = !o ? null : notReady && gOut ? <GapLine gap={gOut} missing /> : notReady ? t('season.notReady') : wetLean > dryLean ? t('season.leansWet') : dryLean > wetLean ? t('season.leansDry') : t('season.noClear');
  const fieldLine = <><b>{fieldName(p.loc)}</b> · {t('season.acresN', { n: acres(p.loc) })}</>;
  return (
    <StepShell id="season" testid="coming-season" resetKey={p.loc.id} onSheet={p.onSheet} onClose={p.onClose} onBack={p.onBack}
      field={fieldLine}
      title={t('season.title')}
      answer={nxt == null ? <Answer headline="" loading /> : rainFed
        ? <Answer tone="good" headline={t('season.yesRain')} sub={today ? t('season.needsNoIrr', { name: rotName(today).replace(/^\w/, (c) => c.toUpperCase()) }) : t('season.itNeedsNoIrr')} />
        : short
          ? <Answer tone="warn" headline={t('season.probNot', { by: g!.by })} sub={t('season.probNotSub', { crop: today ? rotName(today) : t('season.todaysCrop'), n: nxt.toFixed(1), a: p.allocation.toFixed(1), ex: p.exampleLimit ? t('season.exampleP') : '' })} />
          : <Answer tone={even ? 'neutral' : 'good'} headline={even ? t('season.justAbout') : t('season.yesEnough')} sub={t('season.enoughSub', { crop: today ? rotName(today) : t('season.todaysCrop'), n: nxt.toFixed(1), a: p.allocation.toFixed(1), ex: p.exampleLimit ? t('season.exampleP') : '' })} />}
      detailWhat={t('season.detailWhat')}
      next={{ label: t('season.nextCompare'), sub: short ? t('season.findFit') : t('season.seeElse'), onClick: p.onCompare, testid: 'season-to-compare' }}
      detail={<div className="sheet-cols stacked">
        <div className="sheet-col">
          <h3>{t('season.rainTempH')}</h3>
          {gOut && <p><GapLine gap={gOut} missing={notReady} /></p>}
          {!(bc && notReady) && <>
          <ul className="olist">
            {o?.seasons.slice(0, 4).map((s) => {
              const r = lean(s.rain, 'rain'), tl = lean(s.temp, 'temp');
              return (
                <li key={s.season}>
                  <b>{SEASON[s.season] ?? s.season}</b>
                  <span>{t('season.rainLine', { r: r.words, p: s.rain?.prob ? t('season.chanceP', { n: Math.round(s.rain.prob) }) : '', x: tl.words, q: s.temp?.prob ? ` (${Math.round(s.temp.prob)}%)` : '' })}</span>
                </li>
              );
            })}
          </ul>
          <p className="how">{t('season.thirds')}</p>
          <cite>{bc ? t('season.citeBC') : t('season.citeNOAA')}{o?.issued ? t('season.issued', { date: fmtDate(o.issued) }) : ''}{t('season.atField')} <Src p={o?.prov.cpc} /></cite>

          {!(bc && !o?.droughtNow && !o?.droughtOutlook) && <>
          <h3>{t('season.drought')}</h3>
          <dl className="facts">
            <div><dt>{t('season.now')}</dt><dd>{o?.droughtNow ? <>{t('season.droughtIn', { c: o.droughtNow.category.startsWith('None') ? t('season.noDrought') : title(o.droughtNow.category.replace(/^D\d /, '')), place: o.droughtNow.county || place(p.loc) })} <small>({t('season.mapOf', { date: fmtDate(o.droughtNow.date) })})</small></> : t('season.notLoaded')}</dd></div>
            <div><dt>{t('season.outlook')}</dt><dd>{o?.droughtOutlook ? <>{t('season.through', { c: DROUGHT[o.droughtOutlook.category] ?? o.droughtOutlook.category.replace(/_/g, ' '), d: o.droughtOutlook.target })}</> : t('season.notLoaded')}</dd></div>
          </dl>
          <cite>{t('season.citeDrought')} <Src p={o?.prov.water} /></cite>
          </>}
          </>}
        </div>

        <div className="sheet-col">
          {bc ? <>
          <h3>{t('season.ordersH')}</h3>
          <ul className="olist">
            {(wc?.orders ?? []).map((x) => <li key={x.date + x.title} className={x.kind === 'rescission' ? 'rescind' : ''}><b>{fmtDate(x.date)}</b><span>{x.kind === 'rescission' ? `${t('season.rescinded')} ` : ''}{x.title}.{linkOf(x) && <> <a href={linkOf(x)!} target="_blank" rel="noreferrer">{t('week.source')}</a></>}</span></li>)}
            {!wc?.orders?.length && <li><span>{t('season.noneRecord')}</span></li>}
          </ul>
          {wc?.note && <p className="how">{wc.note}</p>}
          <cite>{t('season.citeBCOrders')} <Src p={p.prov.water} /></cite>
          </> : <>

          </>}
          <h3>{t('season.groundH')}</h3>
          <dl className="facts">
            <div><dt>{t('season.rainSince')}</dt><dd>{p.nasaNow?.rainWyMm != null && p.nasaNow.rainWyNormalMm ? <>{t('season.rainOfNormal', { a: (p.nasaNow.rainWyMm / 25.4).toFixed(1), b: Math.round((p.nasaNow.rainWyMm / p.nasaNow.rainWyNormalMm) * 100) })}</> : t('season.notLoaded')}</dd></div>
            <div><dt>{t('season.rootSoil')}</dt><dd>{soil ? <>{band(soil.v, t('season.wetterUsual'), t('season.aboutNormal'), t('season.drierUsual'))} ({t('season.pctile', { o: ordinal(Math.round(soil.v)), n: Math.round(soil.v), when: whenT(soil.t) })})</> : t('season.notLoaded')}</dd></div>
            <div><dt>{t('season.groundwater')}</dt><dd>{gw ? <>{band(gw.v, t('season.aboveUsualC'), t('season.aboutUsualC'), t('season.belowUsualC'))} ({t('season.pctile', { o: ordinal(Math.round(gw.v)), n: Math.round(gw.v), when: whenT(gw.t) })}); {t('season.wholeBasin')}</> : t('season.notLoaded')}</dd></div>
          </dl>
          <cite>{t('season.citeGround', { src: p.regionalLive.soilSource === 'smap' ? t('season.srcSmap') : t('season.srcModel') })} {p.regionalLive.grace ? '' : `${t('season.exampleNums')} `}<Src p={p.prov.regional} /></cite>

          {!bc && <>
          <h3>{t('season.allocH')}</h3>
          {surface && o?.cvpNow && <p className="olead">{t('season.cvp', { a: o.cvpNow.settlement ?? '?', b: o.cvpNow.northAg ?? '?', c: o.cvpNow.southAg ?? '?' })}{o.swpNow ? ` ${t('season.swp', { n: o.swpNow.pct, v: o.swpNow.verified ? '' : t('season.swpNews') })}` : ''}</p>}
          {surface && o?.storageVsAlloc && o.storageVsAlloc.length > 0 && <>
            <p className="how">{t('season.shastaQ')}</p>
            <table className="otable compact">
              <thead><tr><th>{t('season.thMidNov')}</th><th>{t('season.thShasta')}</th><th>{t('season.thSouth')}</th><th>{t('season.thSettle')}</th></tr></thead>
              <tbody>
                {o.storageVsAlloc.filter((r) => !r.partial).slice(-6).map((r) => <tr key={r.year} className={r.shastaPctCap < 35 ? 'low' : ''}><th>{r.year - 1}</th><td>{Math.round(r.shastaPctCap)}%</td><td>{r.southAg ?? '–'}%</td><td>{r.settlement ?? '–'}%</td></tr>)}
                {o.shastaNowAf != null && <tr className="base"><th>{t('season.now2026')}</th><td>{Math.round((o.shastaNowAf / 4552000) * 100)}%</td><td colSpan={2}>{t('season.notAnn2027')}</td></tr>}
              </tbody>
            </table>
          </>}
          {o?.allocations && <p className="how">{o.allocations.next}</p>}
          {o?.allocations && o.allocations.items.length > 0 && <div className="alloc-row">{o.allocations.items.map((a) => <span key={a.year}><b>{a.pct}%</b><small>{a.year}</small></span>)}</div>}
          <cite>{t('season.citeAlloc')} <Src p={o?.prov.alloc} /></cite>

          <h3>{t('season.snowH')}</h3>
          <p className="how">{o?.snow ? `${t('season.snowHolds', { n: o.snow.swe ?? '?', date: o.snow.date })} ` : ''}{t('season.b120', { v: o?.snow?.b120 || t('season.notOut') })}</p>
          </>}
        </div>

        <div className="sheet-col">
          <h3>{t('season.bareH')} <What k="bare" /></h3>
          {o?.bare ? (o.bare.start ? <>
            <p className="big">{t('season.usuallyBare', { a: o.bare.start, b: o.bare.end })}</p>
            <p>{t('season.aboutDays', { n: Math.round(o.bare.days ?? 0) })}{o.bare.low != null ? t('season.pastRange', { a: Math.round(o.bare.low), b: Math.round(o.bare.high ?? 0) }) : ''}. {t('season.rainLanded')} <b>{t('season.pastWinters', { n: Math.round(o.bare.chance ?? 0) })}</b>{o.bare.chanceOutlook != null ? <>; {t('season.outlookLeans', { w: o.seasons.slice(0, 3).filter((x) => x.rain?.category.startsWith('above')).length >= 2 ? t('season.oWet') : o.seasons.slice(0, 3).filter((x) => x.rain?.category.startsWith('below')).length >= 2 ? t('season.oDry') : t('season.oNeither') })}</> : null}.</p>
          </> : <p className="big">{t('season.noBare')}</p>) : allYearsBw && allYearsBw.days > 0 ? <>
            <p className="big">{t('season.usuallyBare', { a: allYearsBw.from, b: allYearsBw.to })}</p>
            <p>{t('season.aboutDays', { n: allYearsBw.days })}. {allYearsBw.chance != null ? <>{t('season.inPre')} <b>{t('season.hitsOf', { a: allYearsBw.hits, b: allYearsBw.winters })}</b> {t('season.inPost')}</> : null}</p>
          </> : allYearsBw ? <p className="big">{t('season.noBare')}</p> : <p>{t('season.loading')}</p>}
          <cite>{o?.bare ? t('season.citeBare1', { a: bc ? 'ECCC' : 'NOAA' }) : t('season.citeBare2', { st: stationsName(p.loc).replace(/ near the field$/, '') })} {t('season.pastRecord')} {BARE_DEF} <Src p={o?.bare ? o.prov.cpc : p.prov.calendar} /></cite>

          <h3>{t('season.irrNeedH')}</h3>
          <table className="otable">
            <thead><tr><th>{t('season.thRotation')}</th>{o?.irrigation && <th>{t('season.thNext')}</th>}<th>{t('season.thTypical')}</th><th>{t('season.thDry')}</th><th>{t('season.thWet')}</th></tr></thead>
            <tbody>
              {p.strategies.map((s) => {
                const n = s.water.irrigation_need_mm, dry = s.exposure.replay['2022']?.irrigation_need_mm, wet = s.exposure.replay['2023']?.irrigation_need_mm;
                const over = mmToAfac(n.value) > p.allocation;
                return (
                  <tr key={s.id} className={s.is_baseline ? 'base' : ''}>
                    <th>{s.short_name}{s.is_baseline && <small> {t('season.today')}</small>}</th>
                    {isRainFed(s) ? <td colSpan={o?.irrigation ? 4 : 3} className="strong">{RAIN_FED}</td> : <>
                    {o?.irrigation && <td className={(o.irrigation[s.id]?.value ?? 0) > p.allocation ? 'warn strong' : 'strong'}>{o.irrigation[s.id] ? `${o.irrigation[s.id].value.toFixed(1)}` : '–'}</td>}
                    <td className={over ? 'warn' : ''}>{mmToAfac(n.low ?? n.value).toFixed(1)}–{mmToAfac(n.high ?? n.value).toFixed(1)}</td>
                    <td>{dry ? mmToAfac(dry.value).toFixed(1) : '–'}</td>
                    <td>{wet ? mmToAfac(wet.value).toFixed(1) : '–'}</td></>}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="how">{t('season.afPerAcre', { n: p.allocation.toFixed(1), ex: p.exampleLimit ? t('season.exampleChange') : '' })} {o?.irrigation ? (() => { const sp = Math.max(...Object.values(o.irrigation).map((x) => x.high - x.low)); return sp < 0.15 ? t('season.moves', { n: sp < 0.1 ? t('season.lessThan') : t('season.about01') }) : t('season.range', { n: sp.toFixed(1) }); })() : ''}</p>
          <cite>{t('season.citeRot')} <Src p={p.prov.strategies} /></cite>
        </div>
      </div>}>
      <KeyFacts facts={[
        ...(r7 === undefined || (r7 && r7.covered) ? [{ label: t('merge.rain7'), value: r7 === undefined ? <span className="skel" /> : <>{r7!.text}<small>{t('merge.noaaFc')}</small></> }] : []),
        { label: t('season.winterRain'), value: rainWords ?? <span className="skel" />, tone: dryLean > wetLean ? 'warn' : undefined },
        { label: t('season.waterSupply'), value: supply },
      ]} />
      {!notReady && o && <p className="step-note">{o.prov.cpc.origin === 'estimate' ? t('season.pastWeather') : t('season.outlooksNot')}</p>}
    </StepShell>
  );
}
