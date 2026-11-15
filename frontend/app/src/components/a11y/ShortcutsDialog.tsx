import { Dialog } from './Dialog';
import { ax } from './ax';

const ROWS: [string, Parameters<typeof ax>[0]][] = [['1 2 3 4 5', 'kStep'], ['/', 'kSearch'], ['l', 'kList'], ['r', 'kRead'], ['?', 'kHelp'], ['Esc', 'kEsc']];
/** The keyboard shortcuts, as a real table so a screen reader can walk it. */
export function ShortcutsDialog({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title={ax('shortcuts')} onClose={onClose} testid="shortcuts-dialog">
      <p>{ax('shortcutsHint')}</p>
      <table className="kbd-table">
        <thead><tr><th scope="col">Key</th><th scope="col">Action</th></tr></thead>
        <tbody>{ROWS.map(([k, a]) => <tr key={k}><th scope="row">{k.split(' ').map((x) => <kbd key={x}>{x}</kbd>)}</th><td>{ax(a)}</td></tr>)}</tbody>
      </table>
    </Dialog>
  );
}
