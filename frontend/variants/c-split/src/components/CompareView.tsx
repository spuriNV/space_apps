import { MM_PER_AF_AC, PRIORITIES, mmToAfAc } from '../api';
import type { Range, ScoreKey, ScoredStrategy } from '../types';
import { ALLOC_TEXT, Icon, MonthStrip, ScoreChip, ScoreRange, TieBadge, WaterBar, allocStatus, fmt, fmtRange, rng, CoverLegend } from './Bits';

export type Replay = 'typical' | '2022' | '2023';
const MORE: { key: ScoreKey; label: string }[] = [{ key: 'pest_break', label: 'Pest-cycle break' }, { key: 'infiltration', label: 'Infiltration' }, { key: 'n_scavenging', label: 'Nitrogen scavenging' }];
const RMA = [
  { k: 'rma_share_drought', label: 'Drought', cls: 'drought' }, { k: 'rma_share_excess_moisture', label: 'Too wet', cls: 'wet' },
  { k: 'rma_share_heat', label: 'Heat', cls: 'heat' }, { k: 'rma_share_other', label: 'Other', cls: 'other' },
] as const;

export default function CompareView({ items, allocation, replay, onReplay, onBrief, onRemove, weights }: {
  items: ScoredStrategy[]; allocation: number; replay: Replay; onReplay: (r: Replay) => void; onBrief: (id: string) => void; onRemove: (id: string) => void; weights: Record<string, number>;
}) {
  const allocMm = allocation * MM_PER_AF_AC;
  const base = items.find((s) => s.is_baseline);
  const need = (s: ScoredStrategy): Range => rng(replay === 'typical' ? s.water.irrigation_need_mm : s.exposure.replay[replay].irrigation_need_mm);
  const rain = (s: ScoredStrategy): Range => rng(replay === 'typical' ? s.exposure.exposed_rain_days : s.exposure.replay[replay].exposed_rain_days);
  const maxRain = Math.max(...items.map((s) => rain(s).high), 6);
  const cols = { gridTemplateColumns: `148px repeat(${items.length}, minmax(0, 1fr))` };
  const Row = ({ label, sub, children, cls = '' }: { label: string; sub?: string; children: (s: ScoredStrategy) => JSX.Element; cls?: string }) => (
    <div className={`crow ${cls}`} style={cols}>
      <div className="clabel">{label}{sub && <small>{sub}</small>}</div>
      {items.map((s) => <div className="ccell" key={s.id}>{children(s)}</div>)}
    </div>
  );
  return (
    <div className="compare">
      <div className="compare-top">
        <div>
          <h2>Compare rotations side by side</h2>
          <p>Bars are ranges, not single numbers. Where ranges overlap, the data cannot pick a winner.</p>
        </div>
        <div className="seg" role="group" aria-label="Replay year">
          <button aria-pressed={replay === 'typical'} onClick={() => onReplay('typical')}>Typical year</button>
          <button aria-pressed={replay === '2022'} onClick={() => onReplay('2022')} data-replay="2022">Replay 2022 <small>drought</small></button>
          <button aria-pressed={replay === '2023'} onClick={() => onReplay('2023')} data-replay="2023">Replay 2023 <small>storms</small></button>
        </div>
      </div>
      <div className="ctable">
        <div className="crow chead" style={cols}>
          <div className="clabel"><CoverLegend /></div>
          {items.map((s) => (
            <div className="ccell" key={s.id}>
              <div className="chead-top">
                <ScoreChip r={s.composite} />
                <div className="chead-name">
                  <h3>{s.name}</h3>
                  <div className="rbadges"><TieBadge s={s} />{s.year_shown && <span className="badge muted">{s.year_shown}</span>}</div>
                </div>
                {items.length > 2 && <button className="iconbtn sm" onClick={() => onRemove(s.id)} aria-label={`Remove ${s.name}`}><Icon name="close" size={13} /></button>}
              </div>
              <MonthStrip s={s} />
            </div>
          ))}
        </div>
        <Row label="Irrigation need" sub={`vs your ${fmt(allocation, 1)} acre-ft/acre`}>
          {(s) => {
            const n = need(s); const st = allocStatus(n, allocMm);
            return (
              <div className="cwater">
                <div className="cbig"><b>{fmtRange(mmToAfAc(n.low), mmToAfAc(n.high), 1)}</b> acre-ft/acre</div>
                <WaterBar need={n} allocMm={allocMm} />
                <div className="csub">{fmtRange(n.low, n.high)} mm · <span className={`st st-${st}`}>{ALLOC_TEXT[st]}</span></div>
              </div>
            );
          }}
        </Row>
        <Row label="Exposed heavy-rain days" sub="bare soil + heavy rain">
          {(s) => {
            const r = rain(s);
            return (
              <div className="crain">
                <div className="cbig"><b>{fmtRange(r.low, r.high)}</b> days</div>
                <div className="rainbar"><i style={{ left: `${(r.low / maxRain) * 100}%`, width: `${Math.max(3, ((r.high - r.low) / maxRain) * 100)}%` }} /><u style={{ left: `${(r.value / maxRain) * 100}%` }} /></div>
              </div>
            );
          }}
        </Row>
        <Row label="OpenET check" sub="measured vs our model">
          {(s) => (s.water.etc_vs_openet_pct
            ? <span className="oet ok"><Icon name="check" size={13} />Model within {Math.abs(s.water.etc_vs_openet_pct.value)}% of OpenET</span>
            : <span className="oet none">No OpenET match for this crop here</span>)}
        </Row>
        <div className="csection">Scores, 0–100 · higher is better<span><i className="basekey" />today's rotation</span></div>
        {PRIORITIES.map((p) => (
          <Row key={p.key} label={p.label} sub={weights[p.key] > 1 ? 'matters most' : undefined} cls={`score${weights[p.key] > 1 ? ' hot' : ''}`}>
            {(s) => <div className="cscore"><ScoreRange r={rng(s.scores[p.key])} baseline={base && !s.is_baseline ? base.scores[p.key].value : undefined} /><b>{s.scores[p.key].value}</b></div>}
          </Row>
        ))}
        {MORE.map((p) => (
          <Row key={p.key} label={p.label} cls="score minor">
            {(s) => <div className="cscore"><ScoreRange r={rng(s.scores[p.key])} tone="grey" baseline={base && !s.is_baseline ? base.scores[p.key].value : undefined} /><b>{s.scores[p.key].value}</b></div>}
          </Row>
        ))}
        <Row label="Insurance losses" sub="2010–2024, not a forecast" cls="rma">
          {(s) => (
            <div className="crma">
              <div className="rmabar">{RMA.map((r) => <i key={r.k} className={`rma-${r.cls}`} style={{ width: `${s.risk_profile[r.k].value}%` }} />)}</div>
              <div className="rmachips">{RMA.slice(0, 3).map((r) => <span key={r.k} className={`rmachip rma-${r.cls}`}><i />{r.label} {s.risk_profile[r.k].value}%</span>)}</div>
              <div className="csub">{s.risk_profile.rma_label}</div>
            </div>
          )}
        </Row>
        <Row label="" cls="cactions">
          {(s) => <button className="btn outline" onClick={() => onBrief(s.id)} data-brief={s.id}><Icon name="doc" size={15} />Open brief</button>}
        </Row>
      </div>
    </div>
  );
}
