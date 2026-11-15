// "NASA data behind this field": each NASA dataset in plain words, how coarse it is, and whether it is live.
// Led by an astronaut photo of the valley around the field (NASA JSC Gateway to Astronaut Photography of Earth).
import type { ISSPhoto } from '../../api';
import type { NasaDataset } from '../../nasa';
import { STATUS_WORDS } from '../../nasa';
import { t } from '../../i18n';

export function ISSFigure({ iss }: { iss: { photo: ISSPhoto; credit: string } | null }) {
  if (!iss) return null;
  const p = iss.photo;
  const [y, m] = p.date.split('-').map(Number);
  const month = t(`ui.month.${m}`);
  return (
    <figure className="iss" data-testid="iss-photo">
      <a href={p.page_url} target="_blank" rel="noreferrer" title={t('ui.iss.open')}>
        <img src={p.url} alt={t('ui.iss.alt', { month, y, features: p.features.toLowerCase() })} loading="lazy" />
      </a>
      <figcaption>
        <b>{t('ui.iss.seen', { month, y })}</b>
        <span>{t('ui.iss.centre', { n: Math.max(1, Math.round(p.miles)) })} {p.features.split(',').map((s) => s.trim().toLowerCase()).filter((s) => s !== 'agriculture').map((s) => s.replace(/\b\w/g, (c) => c.toUpperCase())).slice(0, 3).join(', ')}.</span>
        <cite>{iss.credit}. {t('ui.iss.photo', { id: p.photo_id })}</cite>
      </figcaption>
    </figure>
  );
}

export function NasaList({ list }: { list: NasaDataset[] }) {
  const live = list.filter((d) => d.status === 'live').length;
  return (
    <details className="nasa-more">
      <summary data-testid="nasa-toggle">{t('ui.nasa.all', { n: list.length, live })} <small>{t('ui.nasa.all_sub')}</small></summary>
      <ul className="nasa" data-testid="nasa-list">
        {list.map((d) => (
          <li key={d.id} className={`ns-${d.status}`}>
            <b>{d.name}</b>
            <span>{d.tells}</span>
            <small>{d.scale}. {d.agency}. <em className={`ns-st ${d.status}`}>{STATUS_WORDS[d.status]}</em>{d.note ? ` ${d.note}` : ''}</small>
          </li>
        ))}
      </ul>
    </details>
  );
}
