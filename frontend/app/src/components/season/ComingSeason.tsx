// "Coming season": outlooks for this winter and next season, always labelled as outlooks, not forecasts.
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import type { NasaNow, Outlook, OutlookCat, ProvMap, RegionalLive } from '../../api';
import { whenT } from '../ui/FieldNow';
import type { Daily } from '../../season';
import { bareWindow } from '../../season';
import { TODAY_T, fmtDate, latestAt, mmToAfac, ordinal } from '../../lib';
const band = (v: number, hi: string, mid: string, lo: string) => (v >= 67 ? hi : v > 33 ? mid : lo);
import Icon from '../Icons';
import { Src, county } from '../ui/shared';
import { What } from '../ui/What';
import { BARE_DEF } from '../../bare';

const SEASON: Record<string, string> = { OND: 'Oct–Dec', NDJ: 'Nov–Jan', DJF: 'Dec–Feb', JFM: 'Jan–Mar', FMA: 'Feb–Apr', MAM: 'Mar–May', AMJ: 'Apr–Jun' };
const lean = (c: OutlookCat | null, kind: 'rain' | 'temp') => {
  if (!c || c.category.startsWith('equal')) return { words: 'no lean either way', tilt: 0 };
  const up = c.category.startsWith('above'), weak = (c.prob ?? 40) <= 35;
  const w = kind === 'rain' ? (up ? 'wetter' : 'drier') : (up ? 'warmer' : 'cooler');
  return { words: `${weak ? 'barely leans' : 'leans'} ${w} than normal`, tilt: weak ? 0 : up ? 1 : -1 };
};
const DROUGHT: Record<string, string> = { No_Drought: 'No drought expected', Persists: 'Drought likely to stay', Improvement: 'Drought likely to ease', Removal: 'Drought likely to end', Development: 'Drought likely to develop' };
const maf = (af: number) => (af >= 1e6 ? `${(af / 1e6).toFixed(2)} million acre-feet` : `${Math.round(af / 1000).toLocaleString()} thousand acre-feet`);
const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
const words = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export default function ComingSeason(p: { nasaNow: NasaNow | null; regional: Regional | null; regionalLive: RegionalLive; loc: Location; outlook: Outlook | null; cal: Calendar | null; daily: Daily | null; strategies: RotationStrategy[]; allocation: number; exampleLimit: boolean; prov: ProvMap; onCompare: () => void; onClose: () => void }) {
  const o = p.outlook;
  const soil = p.regional ? latestAt(p.regional.smap_rootzone_pct.values, TODAY_T, 14) : null, gw = p.regional ? latestAt(p.regional.grace_gw_pct.values, TODAY_T, 14) : null;
  const rainLean = o?.seasons.slice(0, 4).map((s) => lean(s.rain, 'rain').tilt) ?? [];
  const wetLean = rainLean.filter((x) => x > 0).length, dryLean = rainLean.filter((x) => x < 0).length;
  const surface = p.loc.water.source === 'surface';
  const headline = !o ? 'Loading the outlooks…' : wetLean > dryLean ? 'NOAA’s outlook leans wetter than normal this winter' : dryLean > wetLean ? 'NOAA’s outlook leans drier than normal this winter' : 'NOAA’s outlook shows no clear lean this winter';
  const bw = p.cal ? bareWindow(p.cal, p.daily, p.cal.years.map((y) => y.year).filter((y) => y >= 2016 && y <= 2025)) : null;
  const allYearsBw = bw;
  return (
    <section className="sheet season" data-testid="coming-season">
      <header className="sheet-head">
        <div>
          <h2>Coming season: what’s likely this winter and next year</h2>
          <p className="sheet-lede">{headline}. <span className="outlook-tag">Outlooks, not forecasts:</span> they tilt the odds, they don’t say what will happen.</p>
        </div>
        <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>
      </header>
      <div className="sheet-cols three">
        <div className="sheet-col">
          <h3>Rain and temperature outlook</h3>
          <ul className="olist">
            {o?.seasons.slice(0, 4).map((s) => {
              const r = lean(s.rain, 'rain'), t = lean(s.temp, 'temp');
              return (
                <li key={s.season}>
                  <b>{SEASON[s.season] ?? s.season}</b>
                  <span>Rain {r.words}{s.rain?.prob ? ` (${Math.round(s.rain.prob)}% chance)` : ''}. Temperature {t.words}{s.temp?.prob ? ` (${Math.round(s.temp.prob)}%)` : ''}.</span>
                </li>
              );
            })}
          </ul>
          <p className="how">Each season is split into a wetter, a middle and a drier third. With no lean each has a 33% chance; 40% means the odds are tilted, not that rain is certain.</p>
          <cite>NOAA Climate Prediction Center 3-month outlooks{o?.issued ? `, issued ${fmtDate(o.issued)}` : ''}, at this field. <Src p={o?.prov.cpc} /></cite>

          <h3>Drought</h3>
          <dl className="facts">
            <div><dt>Now</dt><dd>{o?.droughtNow ? <>{o.droughtNow.category.startsWith('None') ? 'No drought' : title(o.droughtNow.category.replace(/^D\d /, ''))} in {o.droughtNow.county || `${county(p.loc)} County`} <small>(map of {fmtDate(o.droughtNow.date)})</small></> : 'Not loaded'}</dd></div>
            <div><dt>Outlook</dt><dd>{o?.droughtOutlook ? <>{DROUGHT[o.droughtOutlook.category] ?? o.droughtOutlook.category.replace(/_/g, ' ')} through {o.droughtOutlook.target}</> : 'Not loaded'}</dd></div>
          </dl>
          <cite>US Drought Monitor (county) and NOAA seasonal drought outlook. <Src p={o?.prov.water} /></cite>
        </div>

        <div className="sheet-col">
          <h3>Water in storage now</h3>
          <ul className="olist">
            {o?.reservoirs.map((r) => (
              <li key={r.id}>
                <b>{words(r.name)} reservoir</b>
                <span>{r.pctAvg != null ? `${Math.round(r.pctAvg)}% of average for the date` : ''}{r.pctCap != null ? `, ${Math.round(r.pctCap)}% full` : ''}. {maf(r.storageAf)}{r.yearAgoAf ? `; a year ago ${maf(r.yearAgoAf)}` : ''}.</span>
              </li>
            ))}
            {!o?.reservoirs.length && <li><span>Not loaded.</span></li>}
          </ul>
          <cite>California Data Exchange Center (CDEC), {o?.reservoirs[0]?.date ? fmtDate(o.reservoirs[0].date) : 'latest'}; “average” is CDEC’s own for the date. <Src p={o?.prov.water} /></cite>

          <h3>Water in the ground going into winter</h3>
          <dl className="facts">
            <div><dt>Rain since 1 Oct</dt><dd>{p.nasaNow?.rainWyMm != null && p.nasaNow.rainWyNormalMm ? <>{(p.nasaNow.rainWyMm / 25.4).toFixed(1)} in, {Math.round((p.nasaNow.rainWyMm / p.nasaNow.rainWyNormalMm) * 100)}% of normal for the date</> : 'Not loaded'}</dd></div>
            <div><dt>Root-zone soil</dt><dd>{soil ? <>{band(soil.v, 'Wetter than usual', 'About normal', 'Drier than usual')} ({ordinal(Math.round(soil.v))} percentile, {whenT(soil.t)})</> : 'Not loaded'}</dd></div>
            <div><dt>Groundwater</dt><dd>{gw ? <>{band(gw.v, 'Above usual', 'About usual', 'Below usual')} ({ordinal(Math.round(gw.v))} percentile, {whenT(gw.t)}); whole basin, not your well</> : 'Not loaded'}</dd></div>
          </dl>
          <cite>NASA GPM IMERG rain (normal 2001–2025); NASA GRACE-FO {p.regionalLive.soilSource === 'smap' ? 'groundwater and NASA SMAP soil moisture' : 'with a land model, for soil and groundwater'}. {p.regionalLive.grace ? '' : 'Example numbers. '}<Src p={p.prov.regional} /></cite>

          <h3>Water allocations</h3>
          {surface && o?.cvpNow && <p className="olead">This year’s federal (Central Valley Project) allocations: Sacramento River settlement contractors {o.cvpNow.settlement}%, farms north of the Delta {o.cvpNow.northAg}%, farms south of the Delta {o.cvpNow.southAg}%.{o.swpNow ? ` State Water Project: ${o.swpNow.pct}%${o.swpNow.verified ? '' : ' (from a news copy of the DWR release)'}.` : ''}</p>}
          {surface && o?.storageVsAlloc && o.storageVsAlloc.length > 0 && <>
            <p className="how">What Shasta storage in mid November has meant for the next year’s farm allocation before:</p>
            <table className="otable compact">
              <thead><tr><th>Mid Nov of</th><th>Shasta full</th><th>Next year, south of Delta farms</th><th>Settlement contractors</th></tr></thead>
              <tbody>
                {o.storageVsAlloc.filter((r) => !r.partial).slice(-6).map((r) => <tr key={r.year} className={r.shastaPctCap < 35 ? 'low' : ''}><th>{r.year - 1}</th><td>{Math.round(r.shastaPctCap)}%</td><td>{r.southAg ?? '–'}%</td><td>{r.settlement ?? '–'}%</td></tr>)}
                {o.shastaNowAf != null && <tr className="base"><th>2026, now</th><td>{Math.round((o.shastaNowAf / 4552000) * 100)}%</td><td colSpan={2}>2027 not announced yet</td></tr>}
              </tbody>
            </table>
          </>}
          {o?.allocations && <p className="how">{o.allocations.next}</p>}
          {o?.allocations && o.allocations.items.length > 0 && <div className="alloc-row">{o.allocations.items.map((a) => <span key={a.year}><b>{a.pct}%</b><small>{a.year}</small></span>)}</div>}
          <cite>Reclamation CVP allocation table; storage from CDEC. <Src p={o?.prov.alloc} /></cite>

          <h3>Snowpack and spring runoff</h3>
          <p className="how">{o?.snow ? `Statewide snowpack holds ${o.snow.swe ?? '?'} in of water (${o.snow.date}); the snow season has barely started. ` : ''}DWR’s runoff forecast (Bulletin 120) is {o?.snow?.b120 || 'not out yet'}; the first one usually comes in February.</p>
        </div>

        <div className="sheet-col">
          <h3>Longest bare stretch this winter <What k="bare" /></h3>
          {o?.bare ? (o.bare.start ? <>
            <p className="big">Usually bare from {o.bare.start} to {o.bare.end}</p>
            <p>About {Math.round(o.bare.days ?? 0)} days{o.bare.low != null ? ` (${Math.round(o.bare.low)}–${Math.round(o.bare.high ?? 0)} in past winters)` : ''}. A day with 1 inch of rain or more landed in that window in <b>{Math.round(o.bare.chance ?? 0)}% of past winters</b>{o.bare.chanceOutlook != null ? <>; this winter’s outlook leans {o.seasons.slice(0, 3).filter((x) => x.rain?.category.startsWith('above')).length >= 2 ? 'wetter, so the odds are a little higher' : o.seasons.slice(0, 3).filter((x) => x.rain?.category.startsWith('below')).length >= 2 ? 'drier, so the odds are a little lower' : 'neither way'}</> : null}.</p>
          </> : <p className="big">Usually covered or flooded all winter: no regular bare stretch</p>) : allYearsBw && allYearsBw.days > 0 ? <>
            <p className="big">Usually bare from {allYearsBw.from} to {allYearsBw.to}</p>
            <p>About {allYearsBw.days} days. {allYearsBw.chance != null ? <>In <b>{allYearsBw.hits} of the last {allYearsBw.winters} winters</b> at least one day with 1 inch of rain or more fell in that window.</> : null}</p>
          </> : allYearsBw ? <p className="big">Usually covered or flooded all winter: no regular bare stretch</p> : <p>Loading…</p>}
          <cite>{o?.bare ? 'Longest bare run in this field’s satellite calendar each winter, and NOAA station rain 1981–2024.' : 'Satellite calendar of this field, winters 2016–2025, and NOAA station rain.'} Past record, not a forecast. {BARE_DEF} <Src p={o?.bare ? o.prov.cpc : p.prov.calendar} /></cite>

          <h3>Irrigation need next season, by rotation</h3>
          <table className="otable">
            <thead><tr><th>Rotation</th>{o?.irrigation && <th>Next season, with the outlook</th>}<th>Typical year</th><th>Dry like 2022</th><th>Wet like 2023</th></tr></thead>
            <tbody>
              {p.strategies.map((s) => {
                const n = s.water.irrigation_need_mm, dry = s.exposure.replay['2022']?.irrigation_need_mm, wet = s.exposure.replay['2023']?.irrigation_need_mm;
                const over = mmToAfac(n.value) > p.allocation;
                return (
                  <tr key={s.id} className={s.is_baseline ? 'base' : ''}>
                    <th>{s.short_name}{s.is_baseline && <small> today</small>}</th>
                    {o?.irrigation && <td className={(o.irrigation[s.id]?.value ?? 0) > p.allocation ? 'warn strong' : 'strong'}>{o.irrigation[s.id] ? `${o.irrigation[s.id].value.toFixed(1)}` : '–'}</td>}
                    <td className={over ? 'warn' : ''}>{mmToAfac(n.low ?? n.value).toFixed(1)}–{mmToAfac(n.high ?? n.value).toFixed(1)}</td>
                    <td>{dry ? mmToAfac(dry.value).toFixed(1) : '–'}</td>
                    <td>{wet ? mmToAfac(wet.value).toFixed(1) : '–'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="how">Acre-feet per acre a year. Your limit: {p.allocation.toFixed(1)}{p.exampleLimit ? ' (example, change to yours on Compare)' : ''}; brown means over it. {o?.irrigation ? (() => { const sp = Math.max(...Object.values(o.irrigation).map((x) => x.high - x.low)); return sp < 0.15 ? `In the model, this winter’s outlook moves irrigation need by ${sp < 0.1 ? 'less than 0.1' : 'about 0.1'} acre-foot per acre: rain falls mostly before the crop needs water.` : `Outlook range: up to ${sp.toFixed(1)} acre-feet per acre between scenarios.`; })() : ''}</p>
          <cite>Rotation model driven by NASA POWER sun, wind and humidity, weather 2015–2025. Safflower and wheat are upper bounds (stored soil water not counted). <Src p={p.prov.strategies} /></cite>
          <button className="btn primary wide" onClick={p.onCompare}>Compare rotations<Icon name="right" size={16} /></button>
        </div>
      </div>
    </section>
  );
}
