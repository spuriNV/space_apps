import { Dialog } from './Dialog';
import { DisabilityHelp } from '../help/DisabilityHelp';

/** What CropLytics supports for access, and how it was checked. Linked from the menu and the footer of the Pick panel. */
export function AccessibilityPage({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title="Accessibility" onClose={onClose} testid="a11y-page">
      <p>CropLytics is built to work with a keyboard, a screen reader, a phone in bright sun and without colour. Here is what is supported and how we checked it.</p>
      <h3>What is supported</h3>
      <ul>
        <li><b>Outdoor / high contrast</b> (Menu): type about 15% larger, bold dark ink, no light greys. All text meets WCAG AA, and body text meets AAA in this mode. Remembered on this device.</li>
        <li><b>Pause all motion</b> (Menu): stops the ten-year replay, the rain animation, fly-ins and transitions. The device setting "reduce motion" is honoured everywhere as well.</li>
        <li><b>Simple mode</b> (Menu): each step shows only its answer in short sentences and one big button; "Show more" brings the rest back. Farming terms can be tapped for a plain explanation.</li>
        <li><b>Text size</b> (Menu): 100% to 200%, with the layout kept usable. <b>Colours</b>: same as your device, light or dark (the map stays satellite). <b>Easy-to-read type</b>: Atkinson Hyperlegible with wider spacing.</li>
        <li><b>Describe my field</b> (step 2): a short spoken and written summary of the field and this week. <b>Large print</b> (step 5): the adviser page at 18 point or larger, black on white.</li>
        <li><b>Visual alerts:</b> weather alerts and "too wet to work the field" show as a banner with an icon and words, and are announced to screen readers. Nothing depends on sound.</li>
        <li><b>Voice commands</b> in Ask CropLytics: "open compare", "next step", "read this week", "go to my field" and "describe my field", also in Spanish.</li>
        <li><b>Shortcuts:</b> 1 to 5 for the steps, / to find a field, l for the list, r to read the answer aloud, ? for this list. They are off while you type.</li>
        <li><b>No time limits:</b> nothing closes, moves on or expires by itself. Pop-ups stay until you close them, and the tour only moves when you press Next.</li>
        <li><b>Lite mode</b> (Menu): no 3D, replay or rain animation, fewer downloads, and the last field you opened works with no connection. It turns on by itself on a slow connection or Data Saver.</li>
        <li><b>Keyboard:</b> every step, panel, map button (zoom in, zoom out, tilt, reset north, play and pause, layers) and dialog works with Tab, Enter, Space and the arrow keys. Escape closes dialogs and pop-ups. A "Skip to field panel" link is the first stop.</li>
        <li><b>List of fields:</b> the "List" button shows every field, farm and nearby reserve as a list with name, crop, acres and region, so the map is never required.</li>
        <li><b>Find a place:</b> type an address, a place name or "lat, lon" to open that spot.</li>
        <li><b>Shapes as well as colour:</b> field access reads "✓ OK", "~ Marginal", "✕ Too wet"; crop groups use a colour-blind-safe palette with a letter; charts add patterns.</li>
        <li><b>Charts:</b> each has a one-sentence summary for screen readers and a "Show as table" version.</li>
        <li><b>Screen readers:</b> landmarks (header, navigation, main, complementary), one page heading, labelled controls, alt text on images, and polite announcements for loading and results.</li>
        <li><b>Large targets:</b> main controls are at least 48 px.</li>
      </ul>
      <h3>Read aloud</h3>
      <p>Look for the 🔊 Read aloud button under the main answers. It uses your device's own voice.</p>
      <DisabilityHelp />
      <h3>How it was tested</h3>
      <ul>
        <li>Automated: axe-core runs against the Pick and Now screens for Colusa on every change (serious and critical violations fail the check).</li>
        <li>Keyboard walkthrough of the steps, panels, map buttons and dialogs at 1440 and 390 px wide.</li>
        <li>Visual checks of Outdoor mode, and of the pages with colour removed.</li>
        <li>Not yet tested with a panel of people who use assistive technology every day. If something does not work for you, tell us and we will fix it.</li>
      </ul>
    </Dialog>
  );
}
