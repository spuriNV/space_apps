// "Coming season": same workflow as the CA build — winter rain, water supply, next-season need — filled for BC Salmon River.
import type { Calendar, Location, Regional, RotationStrategy } from '../../types';
import type { NasaNow, Outlook, OutlookCat, ProvMap, RegionalLive } from '../../api';
import { whenT } from '../ui/FieldNow';
import type { Daily } from '../../season';
import { bareWindow } from '../../season';
import { TODAY_T, fmtDate, latestAt, mmToAfac, ordinal } from '../../lib';
const band = (v: number, hi: string, mid: string, lo: string) => (v >= 67 ? hi : v > 33 ? mid : lo);
import Icon from '../Icons';
import { Src, isBC, placeLabel } from '../ui/shared';
import { What } from '../ui/What';
import { DockBottom } from '../ui/Dock';
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
  const bc = isBC(p.loc);
  const soil = p.regional ? latestAt(p.regional.smap_rootzone_pct.values, TODAY_T, 14) : null, gw = p.regional ? latestAt(p.regional.grace_gw_pct.values, TODAY_T, 14) : null;
  const rainLean = o?.seasons.slice(0, 4).map((s) => lean(s.rain, 'rain').tilt) ?? [];
  const wetLean = rainLean.filter((x) => x > 0).length, dryLean = rainLean.filter((x) => x < 0).length;
  const surface = p.loc.water.source === 'surface';
  const shasta = !bc ? (o?.reservoirs.find((r) => /shasta/i.test(r.name)) ?? o?.reservoirs[0]) : undefined;
  const supply = !o ? 'Loading…' : bc
    ? 'Fish-protection cuts can stop forage irrigation (Aug 2023). Set your licence on Compare.'
    : surface
      ? `${shasta ? `${words(shasta.name)} is at ${shasta.pctAvg != null ? `${Math.round(shasta.pctAvg)}% of average` : 'an unknown level'} for the date.` : ''}${o.cvpNow?.settlement != null ? ` This year’s federal allocation for Sacramento River settlement contractors was ${o.cvpNow.settlement}%.` : ''}`
      : gw ? `Groundwater in the basin is ${band(gw.v, 'above usual', 'about usual', 'below usual')} for the time of year.` : 'Groundwater reading not available right now.';
  const today = p.strategies.find((s) => s.is_baseline);
  const nxt = today ? o?.irrigation?.[today.id]?.value ?? mmToAfac(today.water.irrigation_need_mm.value) : null;
  const nextNeed = nxt == null ? 'Loading…' : `About ${nxt.toFixed(1)} acre-feet per acre; your limit is ${p.allocation.toFixed(1)}${p.exampleLimit ? ' (an example, change it on Compare)' : ''}. ${nxt > p.allocation ? `About ${(nxt - p.allocation).toFixed(1)} short.` : 'It fits.'}`;
  const headline = !o ? 'Loading…' : wetLean > dryLean ? 'Winter leans wetter' : dryLean > wetLean ? 'Winter leans drier' : 'No clear winter lean';
  const bw = p.cal ? bareWindow(p.cal, p.daily, p.cal.years.map((y) => y.year).filter((y) => y >= 2016 && y <= 2025)) : null;
  const allYearsBw = bw;
  const dryKey = bc ? '2023' : '2022';
  const wetKey = bc ? '2022' : '2023';
  const dryLabel = bc ? 'Restricted, like 2023' : 'Dry like 2022';
  const wetLabel = bc ? 'Open licences' : 'Wet like 2023';
  const rainLine = !o ? 'Loading…' : wetLean > dryLean ? 'Wetter than usual' : dryLean > wetLean ? 'Drier than usual' : 'No clear lean';
  const fitLine = nxt == null ? 'Loading…' : nxt > p.allocation ? `About ${(nxt - p.allocation).toFixed(1)} short` : 'Fits your limit';
  return (
    <section className="sheet season talk" data-testid="coming-season">
      <header className="sheet-head">
        <div>
          <h2>Coming season</h2>
          <p className="sheet-lede">{headline}. <span className="outlook-tag">Odds only.</span></p>
        </div>
      </header>
      <div className="cs-cards" data-testid="season-summary">
        <button type="button" className="cs-card" disabled>
          <small>Winter rain</small>
          <b>{rainLine}</b>
        </button>
        <button type="button" className="cs-card" disabled>
          <small>Water supply</small>
          <b>{bc ? 'Watch for cuts' : 'See note'}</b>
          <span>{bc ? supply : supply}</span>
        </button>
        <button type="button" className="cs-card warn" disabled>
          <small>Next year</small>
          <b>{fitLine}</b>
          <span>{nxt != null ? `${nxt.toFixed(1)} vs ${p.allocation.toFixed(1)} acre-ft/acre` : '…'}{p.exampleLimit ? ' (example)' : ''}</span>
        </button>
      </div>
      <button className="btn primary wide cs-next" onClick={p.onCompare} data-testid="season-to-compare">Compare rotations<Icon name="right" size={16} /></button>
      <DockBottom>
        <div className="bottom-inner">
          <p className="bottom-label">Next</p>
          <p className="bottom-copy">Short on water? Set your real licence on Compare and pick what matters most.</p>
        </div>
      </DockBottom>
      {/* Extra outlook tables stay out of the core path for now */}
      <div className="sheet-cols three d-only" hidden>
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
            {!o?.seasons?.length && <li><span>Not loaded.</span></li>}
          </ul>
          <p className="how">Each season is split into a wetter, a middle and a drier third. With no lean each has a 33% chance; 40% means the odds are tilted, not that rain is certain.</p>
          <cite>NOAA Climate Prediction Center 3-month outlooks{o?.issued ? `, issued ${fmtDate(o.issued)}` : ''}, at this field. <Src p={o?.prov.cpc} /></cite>

          <h3>Drought</h3>
          <dl className="facts">
            <div><dt>Now</dt><dd>{o?.droughtNow ? <>{o.droughtNow.category.startsWith('None') ? 'No drought' : title(o.droughtNow.category.replace(/^D\d /, ''))} in {o.droughtNow.county || placeLabel(p.loc)} <small>(map of {fmtDate(o.droughtNow.date)})</small></> : 'Not loaded'}</dd></div>
            <div><dt>Outlook</dt><dd>{o?.droughtOutlook ? <>{DROUGHT[o.droughtOutlook.category] ?? o.droughtOutlook.category.replace(/_/g, ' ')} through {o.droughtOutlook.target}</> : 'Not loaded'}</dd></div>
          </dl>
          <cite>Seasonal drought outlook at this location. <Src p={o?.prov.water} /></cite>
        </div>

        <div className="sheet-col">
          {bc ? (
            <>
              <h3>Water supply now</h3>
              <p className="olead">{p.loc.water.district}. Forage in this valley runs on surface licences; in a dry summer the province can order a stop to protect fish (as in August 2023).</p>
              {o?.allocations?.items && o.allocations.items.length > 0 && (
                <>
                  <p className="how">Recent seasons as a simple licence story (100 = open, 0 = curtailed):</p>
                  <div className="alloc-row">{o.allocations.items.map((a) => <span key={a.year}><b>{a.pct}%</b><small>{a.year}</small></span>)}</div>
                </>
              )}
              {o?.allocations?.next && <p className="how">{o.allocations.next}</p>}
              <cite>BC Water Sustainability Act licences and fish population protection orders. <Src p={o?.prov.alloc} /></cite>

              <h3>Water in the ground going into winter</h3>
              <dl className="facts">
                <div><dt>Rain since 1 Oct</dt><dd>{p.nasaNow?.rainWyMm != null && p.nasaNow.rainWyNormalMm ? <>{(p.nasaNow.rainWyMm / 25.4).toFixed(1)} in, {Math.round((p.nasaNow.rainWyMm / p.nasaNow.rainWyNormalMm) * 100)}% of normal for the date</> : 'Not loaded'}</dd></div>
                <div><dt>Root-zone soil</dt><dd>{soil ? <>{band(soil.v, 'Wetter than usual', 'About normal', 'Drier than usual')} ({ordinal(Math.round(soil.v))} percentile, {whenT(soil.t)})</> : 'Not loaded'}</dd></div>
                <div><dt>Groundwater</dt><dd>{gw ? <>{band(gw.v, 'Above usual', 'About usual', 'Below usual')} ({ordinal(Math.round(gw.v))} percentile, {whenT(gw.t)}); whole basin, not your well</> : 'Not loaded'}</dd></div>
              </dl>
              <cite>NASA GPM IMERG rain (normal 2001–2025); NASA GRACE-FO {p.regionalLive.soilSource === 'smap' ? 'groundwater and NASA SMAP soil moisture' : 'with a land model, for soil and groundwater'}. {p.regionalLive.grace ? '' : 'Example numbers. '}<Src p={p.prov.regional} /></cite>

              <h3>Snow and spring runoff</h3>
              <p className="how">Interior BC forage depends on mountain snow and local streamflow into the growing season. Watch snowpack reports for the Shuswap and any mid-summer fish-protection notices on the Salmon River.</p>
            </>
          ) : (
            <>
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
              <cite>California Data Exchange Center (CDEC), {o?.reservoirs[0]?.date ? fmtDate(o.reservoirs[0].date) : 'latest'}. <Src p={o?.prov.water} /></cite>

              <h3>Water in the ground going into winter</h3>
              <dl className="facts">
                <div><dt>Rain since 1 Oct</dt><dd>{p.nasaNow?.rainWyMm != null && p.nasaNow.rainWyNormalMm ? <>{(p.nasaNow.rainWyMm / 25.4).toFixed(1)} in, {Math.round((p.nasaNow.rainWyMm / p.nasaNow.rainWyNormalMm) * 100)}% of normal for the date</> : 'Not loaded'}</dd></div>
                <div><dt>Root-zone soil</dt><dd>{soil ? <>{band(soil.v, 'Wetter than usual', 'About normal', 'Drier than usual')} ({ordinal(Math.round(soil.v))} percentile, {whenT(soil.t)})</> : 'Not loaded'}</dd></div>
                <div><dt>Groundwater</dt><dd>{gw ? <>{band(gw.v, 'Above usual', 'About usual', 'Below usual')} ({ordinal(Math.round(gw.v))} percentile, {whenT(gw.t)}); whole basin, not your well</> : 'Not loaded'}</dd></div>
              </dl>
              <cite>NASA GPM IMERG; NASA GRACE-FO / SMAP. <Src p={p.prov.regional} /></cite>

              <h3>Water allocations</h3>
              {surface && o?.cvpNow && <p className="olead">Federal CVP allocations: settlement {o.cvpNow.settlement}%, north of Delta {o.cvpNow.northAg}%, south of Delta {o.cvpNow.southAg}%.</p>}
              {o?.allocations && <p className="how">{o.allocations.next}</p>}
              <cite>Reclamation / DWR allocation tables. <Src p={o?.prov.alloc} /></cite>
            </>
          )}
        </div>

        <div className="sheet-col">
          <h3>Longest bare stretch this winter <What k="bare" /></h3>
          {o?.bare ? (o.bare.start ? <>
            <p className="big">Usually bare from {o.bare.start} to {o.bare.end}</p>
            <p>About {Math.round(o.bare.days ?? 0)} days{o.bare.low != null ? ` (${Math.round(o.bare.low)}–${Math.round(o.bare.high ?? 0)} in past winters)` : ''}.</p>
          </> : <p className="big">Usually covered all winter: no regular bare stretch</p>) : allYearsBw && allYearsBw.days > 0 ? <>
            <p className="big">Usually bare from {allYearsBw.from} to {allYearsBw.to}</p>
            <p>About {allYearsBw.days} days. {allYearsBw.chance != null ? <>In <b>{allYearsBw.hits} of the last {allYearsBw.winters} winters</b> at least one day with 1 inch of rain or more fell in that window.</> : null}</p>
          </> : allYearsBw ? <p className="big">Usually covered all winter: no regular bare stretch</p> : <p>Loading…</p>}
          <cite>Satellite calendar of this field and station rain. Past record, not a forecast. {BARE_DEF} <Src p={o?.bare ? o.prov.cpc : p.prov.calendar} /></cite>

          <h3>Irrigation need next season, by rotation</h3>
          <table className="otable">
            <thead><tr><th>Rotation</th>{o?.irrigation && <th>Next season, with the outlook</th>}<th>Typical year</th><th>{dryLabel}</th><th>{wetLabel}</th></tr></thead>
            <tbody>
              {p.strategies.map((s) => {
                const n = s.water.irrigation_need_mm;
                const dry = s.exposure.replay[dryKey]?.irrigation_need_mm;
                const wet = s.exposure.replay[wetKey]?.irrigation_need_mm;
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
          <p className="how">Acre-feet per acre a year. Your limit: {p.allocation.toFixed(1)}{p.exampleLimit ? ' (example, change to yours on Compare)' : ''}; brown means over it.</p>
          <cite>Rotation model driven by NASA POWER at this field. <Src p={p.prov.strategies} /></cite>
          <button className="btn primary wide" onClick={p.onCompare}>Compare rotations<Icon name="right" size={16} /></button>
        </div>
      </div>
    </section>
  );
}
