import { MM_PER_AF_AC, mmToIn } from '../api';
import type { ScoredStrategy } from '../types';
import { ALLOC_TEXT, Icon, MonthStrip, ScoreChip, TieBadge, WaterBar, allocStatus, fmt, fmtRange, needText, rng, CoverLegend } from './Bits';

export default function RotationList({ items, allocation, compareIds, onToggleCompare, onBrief, onCompare, sortLabel, hoverId, onHover }: {
  items: ScoredStrategy[]; allocation: number; compareIds: string[]; onToggleCompare: (id: string) => void; onBrief: (id: string) => void; onCompare: () => void; sortLabel: string;
  hoverId: string | null; onHover: (id: string | null) => void;
}) {
  const allocMm = allocation * MM_PER_AF_AC;
  const sorted = [...items].sort((a, b) => a.rank - b.rank);
  return (
    <>
      <div className="listbar">
        <span><b>{items.length} rotations</b> · {sortLabel}</span>
        <CoverLegend />
      </div>
      <div className="cards">
        {sorted.map((s) => {
          const need = rng(s.water.irrigation_need_mm);
          const st = allocStatus(need, allocMm);
          const t = needText(need);
          const rain = rng(s.exposure.exposed_rain_days);
          const bare = rng(s.exposure.bare_days_per_year);
          const checked = compareIds.includes(s.id);
          return (
            <article key={s.id} className={`rcard${hoverId === s.id ? ' hover' : ''}${checked ? ' checked' : ''}`} data-strategy={s.id} onMouseEnter={() => onHover(s.id)} onMouseLeave={() => onHover(null)}>
              <div className="rhead">
                <div className="rtitle">
                  <div className="rbadges"><TieBadge s={s} />{s.year_shown && <span className="badge muted">{s.year_shown}</span>}</div>
                  <h2>{s.name}</h2>
                  <p>{s.tagline}</p>
                </div>
                <ScoreChip r={s.composite} />
              </div>
              <div className="rmid">
                <div className="rstrip"><MonthStrip s={s} /></div>
                <div className="rnums">
                  <div className="rnum">
                    <label>Irrigation need <span className={`st st-${st}`}>{ALLOC_TEXT[st]}</span></label>
                    <div className="rnum-v"><b>{t.af}</b><small>{t.mm} · {fmtRange(mmToIn(need.low), mmToIn(need.high))} in</small></div>
                    <WaterBar need={need} allocMm={allocMm} compact />
                  </div>
                  <div className="rnum narrow">
                    <label title={s.exposure.exposed_rain_days.note}>Exposed heavy-rain days</label>
                    <div className="rnum-v"><b>{fmtRange(rain.low, rain.high)}</b><small>per year · bare {fmtRange(bare.low, bare.high)} days</small></div>
                  </div>
                </div>
              </div>
              <div className="rfoot">
                <label className="cmp"><input type="checkbox" checked={checked} onChange={() => onToggleCompare(s.id)} />Compare</label>
                <span className="rfoot-note">{s.water.etc_vs_openet_pct ? `Model within ${Math.abs(s.water.etc_vs_openet_pct.value)}% of OpenET` : 'No OpenET match for this crop here'}</span>
                <button className="btn text" onClick={() => onBrief(s.id)}><Icon name="doc" size={15} />Open brief</button>
              </div>
            </article>
          );
        })}
      </div>
      {compareIds.length >= 2 && (
        <div className="cmptray">
          <span><b>{compareIds.length} selected</b> to compare</span>
          <button className="btn primary" onClick={onCompare} data-action="compare">Compare side by side<Icon name="arrow" size={15} /></button>
        </div>
      )}
      <p className="pane-foot">Allocation {fmt(allocation, 1)} acre-ft/acre = {fmt(allocMm)} mm. Alternatives use modelled cover from the crop calendar; today's rotation uses observed satellite cover.</p>
    </>
  );
}
