import Icon from '../Icons';
import { setPref, usePrefs } from './prefs';

/** The Menu: display preferences (remembered), the list view, and the Accessibility page. */
export function MenuItems({ onList, onAbout, onDone }: { onList: () => void; onAbout: () => void; onDone: () => void }) {
  const prefs = usePrefs();
  return (
    <div className="menu-items" role="group" aria-label="Menu" data-testid="menu-items" onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); onDone(); } }}>
      <label className="mi-switch"><input type="checkbox" checked={prefs.outdoor} onChange={(e) => setPref('outdoor', e.target.checked)} data-testid="outdoor-toggle" /><span className="mi-track" aria-hidden="true" />
        <span><b>Outdoor / high contrast</b><small>Bigger, bolder type for bright sun</small></span></label>
      <label className="mi-switch"><input type="checkbox" checked={prefs.pause} onChange={(e) => setPref('pause', e.target.checked)} data-testid="pause-toggle" /><span className="mi-track" aria-hidden="true" />
        <span><b>Pause all motion</b><small>Stops replay, rain and fly-ins</small></span></label>
      <button className="mi-btn" onClick={() => { onDone(); onList(); }}><Icon name="fields" size={20} /><span><b>List of fields</b><small>Every field and farm, without the map</small></span></button>
      <button className="mi-btn" onClick={() => { onDone(); onAbout(); }} data-testid="about-a11y"><Icon name="info" size={20} /><span><b>Accessibility</b><small>What is supported and how it was tested</small></span></button>
    </div>
  );
}
