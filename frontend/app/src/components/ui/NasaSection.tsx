// "NASA data behind this field": each NASA dataset in plain words, how coarse it is, and whether it is live.
// Led by an astronaut photo of the valley around the field (NASA JSC Gateway to Astronaut Photography of Earth).
import type { ISSPhoto } from '../../api';
import type { NasaDataset } from '../../nasa';
import { STATUS_WORDS } from '../../nasa';

export function ISSFigure({ iss }: { iss: { photo: ISSPhoto; credit: string } | null }) {
  if (!iss) return null;
  const p = iss.photo;
  const [y, m] = p.date.split('-').map(Number);
  const month = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][m - 1];
  return (
    <figure className="iss" data-testid="iss-photo">
      <a href={p.page_url} target="_blank" rel="noreferrer" title="Open this photo at NASA">
        <img src={p.url} alt={`Astronaut photo taken from the International Space Station, ${month} ${y}: ${p.features.toLowerCase()}`} loading="lazy" />
      </a>
      <figcaption>
        <b>Seen from the ISS near your field, {month} {y}</b>
        <span>Centre of the photo about {Math.max(1, Math.round(p.miles))} miles from the field. {p.features.split(',').map((s) => s.trim().toLowerCase()).filter((s) => s !== 'agriculture').map((s) => s.replace(/\b\w/g, (c) => c.toUpperCase())).slice(0, 3).join(', ')}.</span>
        <cite>{iss.credit}. Photo {p.photo_id}, eol.jsc.nasa.gov.</cite>
      </figcaption>
    </figure>
  );
}

export function NasaList({ list }: { list: NasaDataset[] }) {
  const live = list.filter((d) => d.status === 'live').length;
  return (
    <>
      <p className="nasa-lede">{live} of {list.length} NASA datasets feed this screen live; the rest are downloaded or on the way.</p>
      <ul className="nasa" data-testid="nasa-list">
        {list.map((d) => (
          <li key={d.id} className={`ns-${d.status}`}>
            <b>{d.name}</b>
            <span>{d.tells}</span>
            <small>{d.scale}. {d.agency}. <em className={`ns-st ${d.status}`}>{STATUS_WORDS[d.status]}</em>{d.note ? ` ${d.note}` : ''}</small>
          </li>
        ))}
      </ul>
    </>
  );
}
