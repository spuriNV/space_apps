import { useState } from 'react';
import { t } from '../../i18n';

/** The data behind a chart as a real table. Always in the page for screen readers; "Show as table" reveals it for everyone. */
export function ChartTable({ caption, head, rows }: { caption: string; head: string[]; rows: (string | number)[][] }) {
  const [on, setOn] = useState(false);
  return (
    <div className="ct">
      <button type="button" className="btn btn-text btn-sm ct-toggle" aria-pressed={on} onClick={() => setOn(!on)}>{on ? t('ui.a11y.hide') : t('ui.a11y.show')}</button>
      <table className={on ? 'ct-table' : 'sr-only'}>
        <caption>{caption}</caption>
        <thead><tr>{head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, k) => (k === 0 ? <th key={k} scope="row">{c}</th> : <td key={k}>{c}</td>))}</tr>)}</tbody>
      </table>
    </div>
  );
}
