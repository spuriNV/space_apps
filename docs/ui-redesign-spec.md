# CropLytics sidebar and field panel: redesign spec

Status: ready to build. Scope: the field panel (`.fpanel`), the pick list (`.picker2`), the phone bottom sheet and the
controls inside them (buttons, chips, segmented controls, disclosure, status words, list rows). Unchanged: the top bar
layout, the plain-language content and its order, the typefaces (Zilla Slab and Libre Franklin) and the type scale.

What you get in this folder:

| Path | What it is |
|---|---|
| `current/*.png` | The live app on 15 Nov 2026 (https://croplytics-app.onrender.com), desktop 1440x900 and phone 390x844 |
| `mock/index.html` | The static review mock. Open it in a browser; it loads `tokens.css` and `components.css` |
| `mock/tokens.css` | **The tokens.** Drop-in replacement for the `:root` block of `frontend/app/src/styles.css` |
| `mock/components.css` | **The component CSS.** Every selector the team needs, with every state |
| `mock/d-field.png`, `d-detail.png`, `d-picker.png` | After: desktop field panel, scrolled panel, pick list |
| `mock/p-peek.png`, `p-half.png`, `p-full.png`, `p-picker.png` | After: phone sheet at the three snap points, phone pick list |
| `mock/comp-light.png`, `comp-dark.png` | Every component in every state, light and dark |
| `SKILL-replacement.md` | Replacement text for the design skill, so later work does not drift back |
| `scripts/` | The Playwright capture scripts and the contrast checker (`python3 scripts/contrast.py`) |

---

## 1. Diagnosis: what looks bad and why

The user said the sidebar feels square, the green "selected" look is harsh, and the buttons are bad. In the code, each
complaint has a specific cause.

### 1.1 Everything is forced to 2px corners
- `styles.css:18` sets `--radius: 2px`.
- `styles.css:260` then applies `border-radius: var(--radius)` to `.chip, .seg, .seg button, .btn, .icon-btn, .ctl, .ctl-group, .panel, .drawer, .hud, .sheet` and more.
  This one line undoes every rounded shape the older look had. For example, `.pill` is 20px at line 62 and is overridden to 2px at line 259.
- The controls the grower touches most set no radius at all, so they are square boxes:
  - `.action` (`:334`)
  - `.pk-chips button` (`:976`)
  - `.more-detail` (`:877`)
  - `.sq-btn` (`:269`)
  - `.pk-search` (`:972`)
- See `current/desktop-10-ca-panel.png` (the 2x2 footer) and `current/desktop-02-field-list.png` (search and chips).

### 1.2 The green is a slab, not a signal
The spot green `#2f5d34` covers large areas instead of marking small ones:
- **Field panel header.** `.fp-head { background: var(--head-band) }` (`:311`) is a solid green block about 140px tall above every field.
  - On a phone it takes about 30% of the half sheet (`current/phone-10-ca-panel.png`).
  - The grab bar `.fp-grab` (`:1027`) is green as well.
- **Selected filter chip.** `.pk-chips button.on { background: var(--head-band); color: #fff }` (`:979`) turns a 44px square solid green with white text.
  This is the "click on things like that green" moment (`current/desktop-04-chip-selected-green.png`, `current/phone-04-chip-selected-green.png`).
- **Segmented controls** in Compare and This field's year use the same solid-green selected state: `.seg button.on { background: var(--accent) }` (`:137`).
- **Primary button.** "Print for your adviser" is a square solid-green box. Placed next to three square outlined boxes, it reads as a fourth tile, not as the main action.

Taken together, green means "header", "selected", "primary" and "link" all at once, at full strength. Nothing on the panel is calm.

### 1.3 Buttons have no states
- `.action` is a 1px 26%-ink border with left-aligned text.
- Hover only changes the border to green and adds a 12% green tint (`:335`). It is barely visible: `current/desktop-11-action-hover.png` looks the same as the default.
- There is no pressed state (`desktop-12-action-pressed.png`) and no disabled styling beyond the global `opacity: 0.45`.
- **No focus ring anywhere.**
  - `grep focus-visible styles.css` finds a single rule, and that rule *removes* the outline: `.pk-row:focus-visible { outline: none }` (`:747`).
  - Tabbing through the panel shows nothing (`desktop-14-focus-visible.png`).
  - This is an accessibility failure (WCAG 2.4.7), not just a matter of looks.
- The close button `.sq-btn` is 30px at the base size and 36px at 1440. Both are under the 44px target, and it is a square outlined on green.

### 1.4 Rules and borders everywhere
- **Section headings.** Every section heading `.fp-h` draws a 2px black rule above it (`--rule-h`, `:319`).
- **Answers and facts.** Answers and facts have hairlines between them.
- **Glance card.** The glance card is pure `#fff` with a border *and* a shadow (`:797`).
- **Disclosure.** The "More detail" disclosure is a dashed box (`:877`), which reads as a drop zone or placeholder (`desktop-15-ca-more-detail-off.png`).
- **Footer.** A 2px black rule sits on top of the footer (`:473`).

Together, the panel reads as a printed form, which is the intent of the skill. But the controls use the same visual language as the dividers, so nothing looks pressable.

### 1.5 Smaller problems seen in the captures
- **Pick-list row hover.** A row lifts with `translateY(-1px)` and a 16px shadow (`:747`). The rows jump under the pointer, and the hover colour is `#fff` hard-coded.
- **Phone chips.** On a phone the chip counts wrap onto a second line inside the square chips (`phone-02-field-list.png`).
- **Stray block under the pick list.** A paper-coloured block shows below the desktop pick list (`desktop-02-field-list.png`, about y 775-825). It is probably a leftover `.panel` shell behind `.picker2`; worth a quick look while the panel CSS is being replaced.
- **Phone bottom tab bar.** The active tab is shown only by a 3px line over the label (`:1022`). It is easy to miss.
- **Meter tracks and soil bar.** These are square-ended, which adds to the blocky feel.
- **Cascade debt.**
  - `styles.css` has three layers, each overriding the one before:
    1. the old glass theme (lines 1-140)
    2. the bulletin overrides (240-300)
    3. later fixes (450+, 900+, 1080+).
  - Several selectors are defined two or three times. For example, `.facts` appears at `:91` and `:341`, and `.ans` at `:324`, `:457` and `:932`.
  - Replacing a component means deleting all of its copies.

---

## 2. Direction

Keep the paper, the ink, the slab headings and the plain answers. Change only how *controls* look and behave.

1. **Rounded where you touch it, square where you read it.**
   - Buttons, chips, segmented controls, the search field and icon buttons are fully rounded (pills).
   - Cards, list rows and the disclosure have 12px corners. The floating panel has 16px corners, and the phone sheet's top corners are 20px.
   - Text blocks, data bars inside the answers, map labels and the printable brief stay crisp.
2. **Green is ink, not paint.** Each job gets one level of green:
   - **Primary action (one per panel):** filled `#2f5d34`.
   - **Selected:** a pale tonal fill `#e3ecdd` with dark green text `#1d3a21`, plus a check icon on chips.
   - **Links and focus ring:** green text and a green 2px ring.
   - **Top-bar band:** the 3px green band under the top bar stays and is the only "header band".
   - The field panel header becomes paper.
3. **Every control has five visible states:** default, hover, pressed, focus-visible and disabled. Selected is a sixth state where it applies.
   - Hover and pressed are ink state layers at 5% and 10%. This follows the Material 3 state-layer model, toned down for a paper ground.
   - Focus is a 2px paper gap plus a 2px green ring.
4. **Space separates; rules only divide rows.** The 2px section rules, the dashed box and the footer's black rule all go.
   Sections are separated by 24px. Hairlines (14% ink) stay between answer rows and fact rows, where they help the eye track across.

Patterns behind this, from the research (section 9):
- **Filter chips:** Material 3 filter chips (outlined off, tonal container on, check icon).
- **Segmented control:** iOS and shadcn segmented controls (a raised white thumb on a grey track, never a brand fill).
- **Panel header:** the Google Maps place panel (paper header, title, close in the corner, pill action row, sticky compressed header).
- **Phone sheet:** Apple's sheet detents (non-modal, medium and large, grabber).
- **Selected rows:** Linear and Radix, where selection is a tint, not a fill.

---

## 3. Design tokens

Canonical file: `mock/tokens.css`. Paste it over the `:root` block at the top of `styles.css`. Existing token names keep
working (`--panel`, `--accent`, `--accent-soft`, `--tint`, `--radius`, `--shadow`); the new ones are additive.

### 3.1 Colour (light, the web default)

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--panel` | `#f7f6f0` | Paper: panel, sheet, top bar | (ground) |
| `--panel-2` | `#efeee7` | Sunken: search field, disclosure row, segmented track | muted text 5.7:1 |
| `--raised` | `#ffffff` | Cards on paper (glance card), segmented thumb | muted text 6.6:1 |
| `--text` | `#191c16` | Ink | 15.9:1 on panel |
| `--text-2` | `#363a31` | Secondary text | 10.7:1 |
| `--muted` | `#5a5e54` | Labels, source lines | 6.1:1 |
| `--line` | `rgba(25,28,22,.14)` | Row dividers | decorative |
| `--line-soft` | `rgba(25,28,22,.08)` | Card edges | decorative |
| `--outline` | `#84877d` | Chip and input boundaries that must be seen | 3.4:1 (meets 1.4.11) |
| `--accent` | `#2f5d34` | Primary fill, links, focus ring, active tab underline | 7.1:1 as text; white on it 7.7:1 |
| `--accent-hover` / `--accent-pressed` | `#284f2c` / `#22442a` | Primary hover / pressed | white 9.4:1 / 10.7:1 |
| **`--accent-container`** | **`#e3ecdd`** | **Selected state** (chips, rows, segmented in the phone tab bar), tonal buttons | |
| `--accent-container-hover` | `#d7e4d0` | Selected or tonal hover / pressed | |
| `--on-accent-container` | `#1d3a21` | Text on container | 10.3:1 (9.5:1 on hover) |
| `--accent-outline` | `#5f8a5c` | Check icon, the ring on the current thumbnail | 3.3:1 on container, 3.7:1 on panel |
| `--warn`, `--bad`, `--good` | unchanged `#8a5a00`, `#a12a1c`, `#2f5d34` | Status words | 5.5:1, 6.8:1, 7.1:1 |
| `--warn-container` / `--on-warn-container` | `#f4ead6` / `#6b4600` | The single "Example numbers" notice per panel | 7.0:1 |
| `--state-hover` / `--state-pressed` / `--state-strong` | ink at 5% / 10% / 14% | State layers | ink stays at 14:1 or more |
| `--focus-ring` | `0 0 0 2px var(--panel), 0 0 0 4px var(--accent)` | Every focusable control | ring 7.1:1 |

**Why `#e3ecdd` for selected.**
- **It keeps the brand hue but drops the weight.** It is the spot green mixed about 12% into paper, so the eye reads "green = chosen" without a dark slab.
- **The selected chip has three cues, not only colour (WCAG 1.4.1):**
  - the check icon (3.3:1)
  - the 1px outline disappearing
  - the change in text colour
- **It reuses an existing value.** The fill is only 1.12:1 against paper, which is why those other cues are required. It is close to the existing `--head-ink-2` (`#dfe9dc`), so it is not a new colour family.

### 3.2 Colour (dark)

The skill says one look, and the web app stays light. Dark tokens are defined (`[data-theme="dark"]` in `tokens.css`) for the
Android and iOS apps when the OS is in dark mode, and for any later web `prefers-color-scheme` support.
See `mock/comp-dark.png`.

| Token | Dark value | Contrast |
|---|---|---|
| `--panel` / `--panel-2` / `--raised` | `#171a15` / `#20241d` / `#23281f` | |
| `--text` / `--text-2` / `--muted` | `#ecebe3` / `#c9cbc0` / `#a3a69a` | 14.7 / 10.7 / 7.1 :1 |
| `--outline` | `#6c7066` | 3.5:1 |
| `--accent` / `--accent-ink` | `#9fcb9b` / `#10260f` | 9.6:1 as text; 8.8:1 ink on fill |
| `--accent-container` / `--on-accent-container` | `#2b3f2b` / `#cfe6c9` | 8.6:1 |
| `--warn` / `--bad` | `#e0b04a` / `#f08a7a` | 8.8 / 7.2 :1 |
| State layers | paper ink `#ecebe3` at 6 / 12 / 16% | |

Data colours (`lib.ts`: bare, partial, covered, water, the soil colours, the crop record) are **unchanged in both themes**. They are never used for chrome.

### 3.3 Shape

| Token | Value | Applies to |
|---|---|---|
| `--r-xs` | 4px | Season strip and soil bar ends, status squares (2px), legend swatches (2-3px) |
| `--r-sm` | 8px | Thumbnails (`.gl-thumb`, `.pk-thumb`), event rows, tooltips |
| `--r-md` | 12px | Cards (`.glance`), list rows (`.pk-row`), `.more-detail`, menu items, `.notice` |
| `--r-lg` | 16px | Floating panels (`.fpanel`, `.picker2`, Compare, Coming season, Sources sheet), popovers (`.tb-menu`, `.tb-datepop`) |
| `--r-xl` | 20px | Phone bottom sheet, top corners only |
| `--r-full` | 999px | Buttons, chips, segmented track and segments, search field, icon buttons, phone tab pill, meter tracks |

Stays square or 2px: map label boxes (`.pin-text`, `.fp-tag`), the yellow field-selection ticks, the printable brief and data cells.
These are print-on-imagery marks, and the skill's map rules still apply to them.

### 3.4 Elevation

| Token | Value | Use |
|---|---|---|
| `--e1` | `0 1px 2px rgba(25,28,22,.08), 0 1px 1px rgba(25,28,22,.04)` | Glance card, segmented thumb |
| `--e2` | `0 2px 6px rgba(25,28,22,.10), 0 12px 32px rgba(25,28,22,.20)` | Panel floating over the map |
| `--e3` | `0 4px 12px rgba(25,28,22,.14), 0 24px 48px rgba(25,28,22,.24)` | Menus, date picker |
| `--e-sheet` | `0 -2px 8px rgba(25,28,22,.10), 0 -12px 32px rgba(25,28,22,.18)` | Phone sheet |
| `--e-stuck` | `0 1px 0 var(--line), 0 6px 12px -8px rgba(25,28,22,.25)` | Header or footer once content scrolls under it |

The shadows use the ink colour, not pure black, and there is no blur or glass. A panel has no border; the shadow carries the edge against the map.

### 3.5 Spacing

The scale is 4pt: `--s-1` 4, `--s-2` 8, `--s-3` 12, `--s-4` 16, `--s-5` 20, `--s-6` 24, `--s-8` 32.

| Where | Spacing |
|---|---|
| Panel side padding | 20 on desktop, 16 on phone |
| Section gap | 24 |
| Answer row padding | 12 above and below |
| Gap between buttons and chips | 8 |

### 3.6 Type (unchanged scale, weights stated)

| Token | Size / line height | Face, weight | Used for |
|---|---|---|---|
| `--fs-title` | 28 / 1.15 | Zilla Slab 600 | Field name (22 on phone; 20 when the header is stuck) |
| `--fs-head` | 22 / 1.2 | Zilla Slab 600 | Section headings, phone field name |
| `--fs-answer` | 20 / 1.25 | Zilla Slab 600 | Answer sentence, meter values, row titles |
| `--fs-body` | 16 / 1.4 | Libre Franklin 400; buttons 600 | Body, buttons, facts |
| `--fs-small` | 14.5 / 1.4 | Libre Franklin 400; chips and segmented 600 | Questions (`dt`), chips, notes |
| `--fs-fine` | 13 / 1.3 | Libre Franklin 400 | Source lines, meter labels, ids |

### 3.7 Sizes

| Token | Value | Notes |
|---|---|---|
| `--h-btn` | 44 | |
| `--h-btn-sm` | 36 | Hit area grown to 44 with `::before` |
| `--h-chip` | 36 | Hit area 44 |
| `--h-seg` | 40 | Segments 34, hit area 44 |
| `--h-icon-btn` | 40 | Hit area 44 |
| `--panel-w` | `min(460px, 46vw)` | Unchanged from today |

### 3.8 Platform mapping (Compose and SwiftUI)

| Token | Jetpack Compose (Material 3) | SwiftUI |
|---|---|---|
| `--panel` | `colorScheme.surface` | `Color("Panel")` asset (Any / Dark) |
| `--panel-2` | `surfaceContainerHigh` | `Color("Panel2")` |
| `--raised` | `surfaceContainerLowest` | `Color("Raised")` |
| `--text` / `--text-2` / `--muted` | `onSurface` / `onSurfaceVariant` / custom `muted` in a `CompositionLocal` | `Color("Ink")`, `Color("Ink2")`, `Color("Muted")` |
| `--outline` / `--line` | `outline` / `outlineVariant` | `Color("Outline")` / `Color("Line")` |
| `--accent` / `--accent-ink` | `primary` / `onPrimary` | `.tint(Color("Accent"))`, `Color("AccentInk")` |
| `--accent-container` / `--on-accent-container` | **`secondaryContainer` / `onSecondaryContainer`** (stock `FilterChip`, `SegmentedButton`, `FilledTonalButton` and `NavigationBar` pick these up). Also set `primaryContainer` to the same values. | `Color("AccentContainer")` / `Color("OnAccentContainer")` |
| `--warn-container` | `tertiaryContainer` / `onTertiaryContainer` | `Color("WarnContainer")` |
| `--bad` | `error` | `Color("Bad")` |
| `--r-xs` / `--r-sm` / `--r-md` / `--r-lg` / `--r-xl` | `Shapes(extraSmall = 4.dp, small = 8.dp, medium = 12.dp, large = 16.dp, extraLarge = 20.dp)`; pills: `CircleShape` / `RoundedCornerShape(50)` | `RoundedRectangle(cornerRadius: 4/8/12/16/20, style: .continuous)`; pills: `Capsule()` |
| `--e1` / `--e2` / `--e3` | `shadowElevation = 1.dp / 6.dp / 12.dp` (tonalElevation 0, so there is no tint) | `.shadow(color: .black.opacity(0.08), radius: 2, y: 1)` / `(0.18, 16, 8)` / `(0.24, 24, 12)` |
| State layers | M3 default ripple and state layers; set `RippleConfiguration(color = onSurface)` with alpha 0.10 pressed and 0.05 hover | `ButtonStyle` that sets `configuration.isPressed ? .opacity(0.10) overlay` |
| Focus ring | `Modifier.focusRing()` (custom: 2.dp border `primary` at 2.dp offset) | Default focus ring; on iPad with a keyboard, `.focusEffectDisabled()` plus a custom 2pt overlay |
| Type | `FontFamily(Font(R.font.zilla_slab_semibold, FontWeight.SemiBold))` and Libre Franklin 400/600/700. Sizes in `sp`: 28, 22, 20, 16, 14.5, 13 | `Font.custom("ZillaSlab-SemiBold", size: 28, relativeTo: .title)`; 22 `.title2`, 20 `.title3`, 16 `.body`, 14.5 `.subheadline`, 13 `.footnote` (Dynamic Type scales them) |
| `--h-btn` 44 | `Modifier.heightIn(min = 44.dp)`; M3's 48dp minimum touch target is already enforced | `.frame(minHeight: 44)` |
| Motion `--ease-std` | `CubicBezierEasing(0.2f, 0f, 0f, 1f)` | `.timingCurve(0.2, 0, 0, 1, duration: …)` |
| Phone sheet | `BottomSheetScaffold(sheetPeekHeight = 128.dp)` with `AnchoredDraggableState` anchors Peek / Half / Full; `sheetShape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)`; `sheetDragHandle = { BottomSheetDefaults.DragHandle(width = 36.dp, height = 4.dp) }` | `.sheet` with `.presentationDetents([.height(128), .medium, .large])`, `.presentationBackgroundInteraction(.enabled(upThrough: .medium))`, `.presentationCornerRadius(20)`, `.presentationDragIndicator(.visible)`, `.interactiveDismissDisabled()` |

---

## 4. Component specs

Canonical CSS: `mock/components.css`; the selectors there are the selectors to ship. See `mock/comp-light.png` for every state side by side.
Rules shared by every component:
- `transition` uses `--dur-1` (120ms) for colour and `--dur-2` (180ms) for selection, both on `--ease-std`.
- Focus is `:focus-visible { box-shadow: var(--focus-ring) }`.
- `prefers-reduced-motion` reduces durations to 1ms.

### 4.1 Buttons (`.btn` plus a variant)

Base for all variants:
```css
.btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; padding:0 20px;
  border-radius:999px; border:1px solid transparent; font:600 16px/1.2 var(--font-ui); white-space:nowrap; }
.btn:active:not(:disabled) { transform: scale(.98); }
```

| Variant | Default | Hover | Pressed | Focus-visible | Disabled |
|---|---|---|---|---|---|
| `.btn-primary` (one per panel: "Print for your adviser") | bg `--accent`, text white | bg `--accent-hover` | bg `--accent-pressed`, scale .98 | `--focus-ring` | bg `--tint-2`, text `--muted` |
| `.btn-secondary` (tonal: "What's likely this winter", "This field's year", "Compare rotations") | bg `--accent-container`, text `--on-accent-container` | bg `--accent-container-hover` | the same plus a 10% ink layer | ring | bg `--tint-2`, text `--muted` |
| `.btn-outline` (neutral: "Back to today", "Show all", dialogs) | transparent, 1px `--outline`, text `--text` | 5% ink layer | 10% ink layer | ring | border `--line`, text `--muted` |
| `.btn-text` (tertiary: "Sources", "Look under the field in 3D", "What's this?") | transparent, text `--link`, padding 0 12 with -12 margin so the text lines up with the body | 5% ink | 10% ink | ring | text `--muted` |
| `.btn-sm` (modifier) | height 36, padding 0 16, 14.5px; `::before` grows the hit area to 44 | | | | |

Icons sit at 18px with a -4px leading margin, for example the print icon on the primary button.
Never use an icon without a label, except for icon buttons.

### 4.2 Icon button (`.icon-btn`, replaces `.sq-btn` and `.pk-close`)

The button is 40x40 with radius 999. Its `::before` sets `inset: -2px`, giving a 44px hit area. The icon is 20px.

| State | Background | Icon colour |
|---|---|---|
| Default | `--state-hover` (a visible neutral disc, so the close button is findable) | `--text-2` |
| Hover | `--tint-2` | `--text` |
| Pressed | `--state-strong` | `--text` |
| Focus | ring | |
| Disabled | transparent | `--muted` |

`.icon-btn.ghost` has no resting disc. Use it for map-adjacent controls.

### 4.3 Filter chips (`.chip` in `.chips`, replaces `.pk-chips button`)

- **Size:** height 36, plus a 4px `::before` above and below for a 44px hit area. Radius 999, padding 0 16. Text is 14.5px at weight 600, with the count in a `.n` span at weight 400 in `--muted`.
- **Default:** 1px `--outline` border, transparent fill, `--text-2`.
- **Hover:** 5% ink layer, text `--text`.
- **Pressed:** 10% ink layer.
- **Selected** (`aria-pressed="true"`):
  - fill `--accent-container`, border transparent, text and count `--on-accent-container`
  - a leading 16px check icon grows in: width 0 to 16 over 180ms, with left padding going from 16 to 12 so the chip barely changes width
  - selected hover: `--accent-container-hover`
- **Focus:** ring.
- **Disabled:** border `--line`, text `--muted`.
- **Phone:** the `.chips` row is `display:flex; overflow-x:auto; scrollbar-width:none`. It never wraps, and the count stays on the same line.

### 4.4 Segmented control (`.seg`, replaces the green `.seg button.on`)

Used for Typical / Dry / Wet year, Low / Medium / High priorities, rain and heat what-ifs, and Satellite rule / Model in This field's year.

```css
.seg { display:inline-flex; padding:3px; gap:2px; min-height:40px; border-radius:999px; background:var(--panel-2);
  box-shadow: inset 0 0 0 1px var(--line-soft); }
.seg button { min-height:34px; padding:0 16px; border-radius:999px; font:600 14.5px/1 var(--font-ui); color:var(--text-2); }
.seg button.on { background:var(--raised); color:var(--text); box-shadow:var(--e1), inset 0 0 0 1px var(--line-soft); }
```

| State | Style |
|---|---|
| Hover (not selected) | 5% ink, text `--text` |
| Selected | Raised white thumb with an e1 shadow, ink text. **No green fill.** |
| Focus | Ring on the segment |
| Disabled | `--muted` at 0.6 |
| `.seg.small` | Keeps 34px segments; the 13px text is retired and it uses 14.5px |

Semantics: the container gets `role="radiogroup"` and `aria-label`. Each segment gets `role="radio"` and `aria-checked`, and arrow keys move between segments.
Optional: animate a single thumb element sliding between segments with `transform` over 180ms on `--ease-std`.

Why not green: a single-choice control shows *which option is active*, not *an action*. The neutral raised thumb matches iOS and shadcn, and it keeps green for the one primary button.

### 4.5 Cards (`.glance`)

- Background `--raised`, radius 12, padding 12.
- Shadow `--e1` plus `0 0 0 1px --line-soft`. This replaces the 1px border plus the hard-coded `#fff`.
- Inner thumbnail: radius 8, no border.
- The season strip and soil bar get 4px radius with `overflow:hidden`.
- Meter tracks are 8px tall with radius 999, and the fill is also rounded.
- The reference mark is 2px wide with 1px radius and stays square-topped. It is a tick, not a control.

No cards inside cards. The glance card is the only card in the panel.

### 4.6 Field-list rows (`.pk-row`)

| State | Style |
|---|---|
| Default | Padding 12, radius 12, gap 16, transparent. Rows separated by 2px of space, not hairlines. |
| Hover | Flat `--state-hover`. **Remove the `translateY` lift and the shadow.** |
| Pressed | `--state-pressed` |
| Current field (`.on`, also `aria-current="true"`) | Fill `--accent-container`. The thumbnail gets a 2px paper gap and a 2px `--accent-outline` ring. |
| Focus | Ring (replaces today's `outline:none`) |

Inside the row:
- Thumbnail: 112x76 on desktop, 88x60 on phone, radius 8.
- Title: Zilla Slab 20 at weight 600.
- Facts and note: 14.5px.
- Strip cells: 7px tall with 2px radius.

### 4.7 Section headers (`.fp-h`)

```css
.fp-h { display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin:24px 0 8px; padding:0; border:0;
  font:600 22px/1.2 var(--font-head); }
.fp-h:first-child { margin-top:8px; }
```

The 2px ink rule is removed.
- **Trailing action:** an optional `.btn-text` at 14.5px sits on the right (for example "Look in 3D"). Today it is a `<small><button class="link">` under the title.
- **Helper line:** a helper sentence ("Click one to move the timeline.") moves to a `.fp-sub` paragraph under the heading in 14.5px `--muted`.

### 4.8 More detail disclosure (`.more-detail`)

- **Layout:** a full-width row, min-height 56, padding 12 16, radius 12. No border.
- **Background:** `--panel-2`.
- **Content:** a title in `b` (16px 700, `--link`), the three-word teaser in `small` (14.5px, `--muted`), and a 20px chevron-down on the right.
- **States:**
  - Hover: `--tint-2`.
  - Pressed: `--state-strong`.
  - Expanded (`aria-expanded="true"`): the chevron rotates 180° over 180ms, and the label changes to "Less detail" (copy as today).
  - Focus: ring.
- **Revealed content:** fades in over 240ms (`opacity` only; no height animation, because the content is long).

### 4.9 Data status (`.status` replaces `.src-tag` and `.ex-limit`)

These stay words, not pills, as the skill requires.
- **Measured / live:** no word.
- **Estimated:** `.status.estimate` is italic in `--muted` with a 10px dashed-outline square (2px radius) before it, followed by "Estimated."
- **Example:** `.status.example` is italic in `--warn` with a 10px hatched square (2px radius) before it, followed by "Example numbers." or "example, change it on Compare".
- **Panel-level example notice:** when the whole server is down, the notice `.notice` appears **once** per panel in the pick list or at the top of the field panel. It has a `--warn-container` fill, radius 12, padding 12 16 and 14.5px text in `--on-warn-container`. It replaces `.offline-note`.

### 4.10 Panel header (`.fp-head`, the field name and actions)

- **Background:** `--panel`, **not green**. Padding 20 20 12.
- **Title row:** `h1` in Zilla Slab 28 at weight 600, and the close `.icon-btn` aligned to the top.
- **Facts line:** 16px `--text-2`, with "149 acres" in 700 ink.
- **Id line:** 13px `--muted`.
- **Sticky behaviour:** the header is already outside `.panel-scroll`, so it never scrolls away. When `.panel-scroll.scrollTop > 8`, add `.stuck` to `.fpanel`:
  - the title becomes 20px on one line with an ellipsis
  - the id line hides
  - the facts become 14.5px
  - padding becomes 12
  - the header gets the `--e-stuck` edge
  - all of this transitions over 240ms
  - remove `.stuck` at 0
- **Actions:** the footer (`.fp-foot`) stays fixed at the bottom.
  - Background `--panel`, top edge `0 -1px 0 var(--line)`. While content runs underneath it, it gets `.stuck` with an upward soft shadow.
  - `.actions` is `display:flex; flex-wrap:wrap; gap:8px`, and each `.btn` is `flex:1 1 auto`.
  - Order: the three `.btn-secondary` first, then the `.btn-primary` with a print icon.
  - At 460px this lays out as two rows: "What's likely this winter" + "This field's year", then "Compare rotations" + "Print for your adviser" (`mock/d-field.png`).
  - Footer padding is 12 16 16.

### 4.11 Bottom tab bar (phone, `.mob-tabs`)

- Height 64.
- Each label sits inside a `span`. For the active tab, that span becomes a 32px-tall pill with `--accent-container` fill and `--on-accent-container` text, which is the Material 3 navigation-bar indicator.
- The 3px top line is removed.
- Disabled tabs (no field picked) are at 0.45.
- Each tab is at least 48px tall.

### 4.12 Search field (`.pk-search`)

| State | Style |
|---|---|
| Default | Height 48, radius 999, `--panel-2` fill, inset 1px `--line-soft`, 18px search icon in `--muted`, 16px input text |
| Hover | Inset 1px `--outline` |
| Focus-within | Fill `--raised`, inset 2px `--accent` |

---

## 5. Layout

### 5.1 Desktop

```
┌ top bar (unchanged) ────────────────────────────────────────────┐
├─ 3px green band ────────────────────────────────────────────────┤
│ ┌ .fpanel  min(460px,46vw), left 12, top bar+3+12, bottom 12 ┐  │
│ │ .fp-head   paper, title + close, facts, id   (sticky)     │  map
│ │ ───────── (edge appears only when .stuck)                 │  │
│ │ .panel-scroll  padding 0 20 20                            │  │
│ │   Your field now · glance card · answers · More detail    │  │
│ │   (detail: NASA data · About the ground · last 3 seasons  │  │
│ │    · events · Sources · footnote)                         │  │
│ │ .fp-foot   sticky, 2 rows of pills                        │  │
│ └───────────────────────────────────────── radius 16, e2 ──┘  │
```

- `.fpanel` and `.picker2` share the same geometry: `left: 12px; top: calc(var(--bar-h) + 3px + 12px)`. `.fpanel` gets `bottom: 12px`, while `.picker2` uses `max-height` so it can be shorter than the screen.
  This replaces today's `top: 64px; bottom: 108px` (`:310`, `:472`), so the panel now uses the full height down to 12px above the bottom.
- `App.tsx` keeps `leftInset = min(460, innerWidth*0.46) + 24`.
- Compare, Coming season and the Sources sheet follow the same surface rules: radius 16, `--e2`, a paper header with an `.icon-btn` close, and `.seg` controls.

### 5.2 Phone (up to 640px): bottom sheet

| Snap | Height | Shows |
|---|---|---|
| Peek | 128px above the tab bar | Grabber, field name (one line, ellipsis), facts line, close |
| Half (default after picking a field) | 52% of the viewport | Plus a sideways-scrolling action-pill row (primary first) and the start of "Your field now" |
| Full | `100% - bar - tabs - 8px` | Header compresses (`.stuck`), all content scrolls |

- **Surface:** `--panel`, top corners `--r-xl` 20, `--e-sheet`, no border. The green grab bar becomes a 36x4 handle in `--outline` at 60% opacity, inside a 28px touch strip, with an extra 16px invisible hit area below it as today.
- **Interaction:**
  - **Drag the handle or header with pointer events:**
    - The sheet follows the finger.
    - On release, it snaps to the nearest snap point, or to the next one in the fling direction if velocity exceeds 0.5 px/ms.
    - The snap animates over 320ms on `--ease-out`.
  - **Tap the handle:** cycles peek → half → full → peek, as today (keep the tap behaviour for accessibility).
  - **Keyboard:** the handle is a button with `aria-label="Resize the field panel"`; Up and Down arrows step between snap points.
- **Scroll locking:** the content only scrolls at Full. At Half, a drag up on the content moves the sheet first, then the content scrolls (the Google Maps behaviour).
- **Non-modal:** the map stays live above the sheet. The map's `bottomInset` follows the sheet height so the selected field stays visible.
- **Actions:** at Half and Full, the actions show as `.sheet-actions`, a horizontal pill row under the header, primary first:
  - The pills are 40px tall with 14.5px text; with the row's padding the touch target is 44px or more.
  - This brings back the next steps that `.fp-foot { display:none }` currently hides on phone (`:1031`).
  - The bottom tab bar still carries the sections.
- **Pick list:** `.picker2` is inset 8px on each side, with radius 16 and its bottom 8px above the tab bar. The chips scroll sideways and the thumbnails are 88x60 (`mock/p-picker.png`).

---

## 6. Motion

| What | Duration | Easing |
|---|---|---|
| Hover / press colour, state layers | 120ms (`--dur-1`) | `cubic-bezier(.2,0,0,1)` |
| Chip select (check grows), segmented thumb, chevron rotate, tab pill | 180ms (`--dur-2`) | `--ease-std` |
| Header compress / uncompress, detail content fade | 240ms (`--dur-3`) | `--ease-std` |
| Panel enter (fade plus 8px slide from the left), sheet snap | 320ms (`--dur-4`) | enter `cubic-bezier(.05,.7,.1,1)`, leave 200ms `cubic-bezier(.3,0,.8,.15)` |
| Button press | `transform: scale(.98)` | 120ms |

Animate only `opacity`, `transform`, `background-color`, `box-shadow` and `font-size` (header only).
Do not animate `height` on long content. With `prefers-reduced-motion: reduce`, all durations become 1ms and the panel enters without a slide.

---

## 7. Accessibility

- **Contrast** (all computed; `scripts/contrast.py` reproduces them):
  - Light theme:
    - Ink 15.9:1, secondary 10.7:1, muted 6.1:1 (5.7:1 on `--panel-2`).
    - Links 7.1:1.
    - White on primary 7.7:1 (9.4:1 on hover).
    - Selected text on container 10.3:1.
    - Warn 5.5:1, notice text 7.0:1.
    - Chip outline 3.4:1 and check icon 3.3:1 (non-text, 3:1 or more).
    - Focus ring 7.1:1.
  - Dark theme: ink 14.7:1, muted 7.1:1, accent 9.6:1, on-container 8.6:1, outline 3.5:1.
- **Not colour alone:**
  - Selected chips add a check icon and lose their outline.
  - The current field row adds a ring on its thumbnail.
  - The active phone tab adds a pill shape.
  - Example data keeps its hatched square and its words.
- **Targets:**
  - Every button 44px or more.
  - Chips 36px visual with a 44px hit area.
  - Icon buttons 40px visual with a 44px hit area.
  - Segments 34px visual with a 44px hit area.
  - Phone tabs 48px.
  - Sheet handle strip 28px plus a 16px extension.
  - Event rows 48px or more.
- **Focus:** a visible `:focus-visible` ring on every interactive element. Delete `outline:none` from `.pk-row:focus-visible`. Keep `outline:0` on inputs only because their container (`.pk-search:focus-within`) shows the ring.
- **Semantics:**
  - Chips use `aria-pressed`.
  - Segmented controls use `radiogroup` and `radio` with `aria-checked`.
  - The current row uses `aria-current="true"`.
  - The disclosure uses `aria-expanded` (already present).
  - The close button gets `aria-label="Close"`; today it only has `title`.

---

## 8. File-by-file change list

Line numbers refer to `frontend/app/src/styles.css` as of 15 Nov 2026. Because several selectors are defined two or
three times, **delete every old copy** of a selector and paste the new block from `mock/components.css` once, near the end of the file.

### `styles.css`

| Lines | Selector(s) | Change |
|---|---|---|
| 4-19 | `:root` | Replace with `mock/tokens.css` (`:root` block). This removes `--radius: 2px`; `--radius` becomes `var(--r-md)`. |
| 260 | `.chip, .seg, .seg button, .btn, .icon-btn, .ctl, … { border-radius: var(--radius) }` | **Delete.** Each component sets its own radius from the scale. |
| 259, 62-63, 66 | `.pill`, `.reopen` | `.reopen` becomes `.btn.btn-outline` on `--panel` with `--e2`. |
| 69-73, 310, 318, 472, 901 | `.panel`, `.fpanel`, `.panel-scroll` | Use the new `.fpanel` and `.panel-scroll` (radius 16, `--e2`, no border, full height, padding 0 20 20). |
| 311-317, 1029-1030, 1083, 1086 | `.fp-head`, `.fp-title`, `.fp-facts`, `.fp-id` | Paper header; add `.fpanel.stuck` rules. |
| 319-321, 461-462, 478 | `.fp-h`, `.fp-h small` | New `.fp-h` without a rule; add `.fp-sub`. |
| 269-270, 314, 911, 1087 | `.sq-btn` | Replace with `.icon-btn` (keep `.sq-btn` as an alias until every sheet is migrated). |
| 333-340, 473-477, 930-931 | `.actions`, `.action`, `.action.primary`, `.fp-foot` | Use `.fp-foot` and `.actions` plus `.btn-*`. Delete `.action*`. |
| 1031 | `.fp-foot { display:none }` (phone) | Keep, and add `.sheet-actions` instead. |
| 323-330, 457-459, 479, 932-935, 965-969 | `.ans`, `.ans b i`, `.sb-key`, `.soil-rot` | Merge into one block; swatch radius 3, `.soil-rot` border-left becomes a 2px `--line` with 4px radius. |
| 91-94, 341-346, 912 | `.facts` | Delete the first copy (91-94); new block with 10px row padding and a 112px label column. |
| 355-359, 914 | `.evlog button` | Radius 8, 48px minimum height, hover is a state layer, chevron. |
| 797-825, 927-929, 937, 943 | `.glance`, `.gl-*`, `.meter`, `.m-*` | Card radius 12 plus `--e1`, rounded strips and tracks, thumbnail radius 8. |
| 877-881, 1091 | `.more-detail` | New disclosure row with a chevron. |
| 300-303, 1100-1101, 630-631 | `.src-tag.*`, `.ex-limit` | Replace with `.status.estimate` and `.status.example` (keep the old class names as aliases). |
| 189, 860 | `.link`, `.sources-link` | Inline links stay `.link`. Buttons that act (Sources, Look under the field in 3D, Back to today, Show all) become `.btn.btn-text` or `.btn.btn-outline.btn-sm`. |
| 132-139, 278, 1052, 1057, 1088 | `.seg`, `.seg button`, `.seg button.on`, `.seg.small` | New segmented control (raised thumb, no green). |
| 76-81 | `.chip.*` (status chips used in Compare and Coming season) | Radius 999, height 28, keep the colour variants. |
| 736-765, 902, 940-941, 1034-1037, 1108 | `.picker2`, `.pk-*` | New pick list: radius 16, flat hover, tonal current row, thumbnail radius 8. |
| 971-980 | `.pk-filter`, `.pk-search`, `.pk-chips*` | New search pill; `.pk-chips` becomes `.chips` and the buttons become `.chip`. |
| 1019-1022 | `.mob-tabs` | Pill indicator. |
| 1026-1028, 1082, 1084-1085 | `.fpanel.sheet-*`, `.fp-grab` | 20px top corners, `--e-sheet`, grey handle, snap heights 128 / 52% / full. |
| 699-706 | `.tb-menu` (field switcher menu) | Radius 16, `--e3`, menu items radius 8 with a state-layer hover, `.on` uses `--accent-container`. Layout unchanged. |
| 715-716 | `.tb-layers`, `.tb-date` | Optional, for consistency: radius 999 and hover state layer. Top-bar layout unchanged. |
| new | `:focus-visible` | Add the global focus rule and the `prefers-reduced-motion` rule from the top of `components.css`. |

### Components (markup only; no copy changes)

- **`components/ui/Options.tsx` (`FieldPanel`):**
  - `sq-btn` becomes `icon-btn`, and add `aria-label="Close"`.
  - Add an `onScroll` on `.panel-scroll` that toggles `stuck` on the section (`scrollTop > 8`), plus `.fp-foot.stuck` while `scrollTop + clientHeight < scrollHeight - 1`.
  - Replace the cycling `fp-grab` button with pointer-event drag and snap (the tap still cycles).
  - Render `<Actions variant="row" />` inside `.panel-scroll` on phone as `.sheet-actions`.
  - "About the ground" trailing link becomes `<button className="btn btn-text">`.
  - "What happened around here" `<small>` becomes `<p className="fp-sub">`.
  - "Sources" becomes `btn btn-text`.
- **`components/ui/Options.tsx` (`FieldPicker`):**
  - `pk-close` becomes `icon-btn`.
  - Chips: `className="chip"`, `aria-pressed`, a leading `<Icon name="check" className="check" size={16} />`, and the count in `<span className="n">`.
  - The `.pk-chips` container becomes `.chips`.
  - `.pk-row` gets `aria-current` when selected.
  - "Show all" becomes `btn btn-outline btn-sm`.
  - `.offline-note` becomes `.notice`.
- **`components/ui/shared.tsx`:**
  - `Actions` renders `<button className={`btn ${a.id === 'brief' ? 'btn-primary' : 'btn-secondary'}`}>`.
  - The `span>b` wrapper is dropped, and the primary gets `<Icon name="brief" />`, or a new `print` icon.
  - Order: season, year, compare, brief (as today).
  - `Src` uses `className="status estimate"` or `"status example"`.
- **`components/ui/Detail.tsx`:** `MoreDetail` renders `<span><b>{label}</b><small>{teaser}</small></span><Icon name="down" size={20} />`.
- **`components/ui/FieldNow.tsx`:** `em.ex-limit` becomes `em.status.example`. `Meter` markup is unchanged; the CSS rounds it.
- **`components/compare/ComparePanel.tsx`, `components/year/YearSheet.tsx`:**
  - `.seg` gets `role="radiogroup"` and `aria-label`.
  - Each button gets `role="radio"` and `aria-checked`, with arrow-key handling (a small shared `Seg` component in `components/ui/` is the cleanest way to do it).
  - `sq-btn` becomes `icon-btn`.
- **`components/season/ComingSeason.tsx`, `components/brief/RotationBrief.tsx`, `components/ui/Sources.tsx`:** `sq-btn` becomes `icon-btn`.
- **`components/Icons.tsx`:** `check`, `down` and `right` exist already. Add `print` if `brief` does not read as a printer.
- **`App.tsx`:**
  - `.mob-tabs` labels are wrapped in `<span>`.
  - `.reopen` becomes `className="reopen btn btn-outline"`.
  - The `bottomInset` on phone follows the sheet's snap height, which `FieldPanel` reports through a callback.
- **`.claude/skills/fieldshift-visual-design/SKILL.md`:** apply `SKILL-replacement.md`.

### Checks after the change
- **Screenshots:** `node design/tools/shoot-app.mjs field-now` and `overview` should match `mock/d-field.png` and `mock/d-picker.png`.
- **Keyboard:** tab through the panel and confirm every control shows the ring.
- **Phone:** at 390px nothing scrolls sideways except `.chips` and `.sheet-actions`.
- **Lint:** `grep -n "head-band" styles.css` should only match the top bar band and the wordmark.

---

## 9. Research notes and sources

The numbers below were confirmed in the source files unless they are marked "memory". The full notes are summarised here.

| Source | Values used | Takeaway |
|---|---|---|
| Material 3 tokens (material-web `tokens/versions/v0_192`; androidx `compose/material3/.../tokens`) | Corner scale 4 / 8 / 12 / 16 / 20 / 28 / full. Buttons 40 tall, full corner. Filter chip 32 tall, 8 corner, selected = secondary-container with no outline. Segmented 40, full corner. Filled card 12. Bottom sheet top 28 and handle 32x4. Icon button 40. List rows 56 / 72 / 88. State layers: hover 0.08, focus and pressed 0.10 (Compose) or 0.12 (older web). Easing standard `(0.2,0,0,1)`, decelerate `(0.05,0.7,0.1,1)`, accelerate `(0.3,0,0.8,0.15)`. Durations short 50-200ms, medium 250-400ms. | Selection is a tonal container, never the primary colour; buttons are pills. |
| Apple HIG: buttons, sheets, segmented controls, accessibility | 44x44pt minimum hit target; sheet detents medium and large, plus custom; non-modal sheets keep the content behind them usable; segmented controls have equal-width segments, 5 or fewer on iPhone. | Phone sheet with peek / half / full over a live map; 44pt targets. |
| Radix Themes (github radix-ui/themes) | Radius 3 / 4 / 6 / 8 / 12 / 16. Buttons 24 / 32 / 40 / 48. Focus is a 2px outline. "Soft" button: accent-a3 background, a4 hover, a5 pressed. Segmented control: gray-a3 track with a raised indicator, 100ms. | Selection is a translucent tint or a raised neutral thumb. |
| shadcn/ui new-york-v4 | Base radius 10. Button h-9 (36) or h-10 (40), rounded-md. Tabs: bg-muted track with a white `shadow-sm` active pill. Toggle "on" is neutral `bg-accent`. | The brand colour is kept for primary actions only. |
| Linear, "Behind the latest design refresh" | Warmer, less saturated greys; a dimmer sidebar; fewer separators with softer contrast. | Take borders and colour away; don't add them. |
| Google Maps (Places UI Kit docs: 250-400px details width, sample 400px; 9to5Google, Mar 2025: rounder sheet corners and an × close button) | Panel around 400-460px. Paper header with a close button in the corner. Pill action row. Sticky compressed header. Tabs with an underline (memory). | The model for the header, actions and sheet. |
| Felt 2.0 (felt.com/blog/ui-upgrades) | One left pane (layers, legend, list), smaller toolbar icons | One quiet panel. |
| Climate FieldView, OneSoil, John Deere Operations Center | Field lists grouped and searchable by farm or crop, with name plus acres per row. OneSoil sorts by crop, NDVI and yield. | Green means crop and brand, not UI selection. Rows lead with the name and acres, as ours already do. |
| Mapbox Studio, Windy, Strava, FBN, Regrow | Nothing citable found in this pass | |

Not adopted, and why:
- **Material 3's 28px sheet corner and the Expressive shape morphing.** Too soft for the bulletin look; 20px and a static radius are used instead.
- **Google Maps' stacked circular icon-plus-label action buttons.** The skill bans stacked icon-plus-label buttons, and the grower's words need room; text pills are used instead.
- **A tab strip inside the panel.** The top bar already holds the sections, and the user likes it.
