import { Dialog } from './Dialog';

/** What CropLytics supports for access, and how it was checked. Linked from the menu and the footer of the Pick panel. */
export function AccessibilityPage({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title="Accessibility" onClose={onClose} testid="a11y-page">
      <p>CropLytics is built to work with a keyboard, a screen reader, a phone in bright sun and without colour. Here is what is supported and how we checked it.</p>
      <h3>What is supported</h3>
      <ul>
        <li><b>Outdoor / high contrast</b> (Menu): type about 15% larger, bold dark ink, no light greys. All text meets WCAG AA, and body text meets AAA in this mode. Remembered on this device.</li>
        <li><b>Pause all motion</b> (Menu): stops the ten-year replay, the rain animation, fly-ins and transitions. The device setting "reduce motion" is honoured everywhere as well.</li>
        <li><b>Keyboard:</b> every step, panel, map button (zoom in, zoom out, tilt, reset north, play and pause, layers) and dialog works with Tab, Enter, Space and the arrow keys. Escape closes dialogs and pop-ups. A "Skip to field panel" link is the first stop.</li>
        <li><b>List of fields:</b> the "List" button shows every field, farm and nearby reserve as a list with name, crop, acres and region, so the map is never required.</li>
        <li><b>Find a place:</b> type an address, a place name or "lat, lon" to open that spot.</li>
        <li><b>Shapes as well as colour:</b> field access reads "✓ OK", "~ Marginal", "✕ Too wet"; crop groups use a colour-blind-safe palette with a letter; charts add patterns.</li>
        <li><b>Charts:</b> each has a one-sentence summary for screen readers and a "Show as table" version.</li>
        <li><b>Screen readers:</b> landmarks (header, navigation, main, complementary), one page heading, labelled controls, alt text on images, and polite announcements for loading and results.</li>
        <li><b>Large targets:</b> main controls are at least 48 px.</li>
      </ul>
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
