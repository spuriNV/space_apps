# Replacement text for `.claude/skills/fieldshift-visual-design/SKILL.md`

Apply these edits so the skill matches the sidebar redesign (`REDESIGN.md`). Each block quotes the current text exactly
and gives the replacement. Everything not listed here (content rules, units, sources, typefaces, type scale, top bar
layout, data colours, the "Do not" list apart from item 10) stays as it is.

---

## Edit 1: the opening line

**Replace**

> One look only: the "Extension bulletin" style (spot-green header band, slab headings, paper panel). There are no theme options and no `?theme=` switch.

**With**

> One look only: the "Extension bulletin" style: paper panels, slab headings, black ink and one spot green used as ink
> (a 3px band under the top bar, the one primary button, links, the focus ring), never as a large fill. Controls are
> rounded and calm; text, data and map marks stay crisp like print. There are no theme options and no `?theme=` switch on
> the web. The native apps may follow the OS dark mode with the dark tokens in section 3.

## Edit 2: section 3, the palette bullets

**Replace**

> - **Extension bulletin:** paper `#f7f6f0`, black ink `#191c16`, one spot green `#2f5d34` (header band, primary action, links,
>   "live"), brown `#8a5a00` only for "example numbers" and "over the limit", red `#a12a1c` for problems.

**With**

> - **Extension bulletin:** paper `#f7f6f0` (`--panel`), sunken paper `#efeee7` (`--panel-2`), white `#ffffff` for the one
>   card per screen (`--raised`), black ink `#191c16`, one spot green `#2f5d34` (`--accent`), brown `#8a5a00` only for
>   "example numbers" and "over the limit", red `#a12a1c` for problems.
> - **Green has three strengths, one job each:**
>   - filled `--accent` = the single primary action on a panel ("Print for your adviser");
>   - tonal `--accent-container` `#e3ecdd` with `--on-accent-container` `#1d3a21` text = **selected** (filter chip on,
>     current field row, active phone tab) and secondary buttons;
>   - green text or a 2px green ring = links and keyboard focus. The 3px band under the top bar is the only green band.
>   Never use solid green as a selected state, a panel header, a sheet handle or a segmented-control thumb.
> - **States are ink layers:** hover = ink at 5% over the element's own fill, pressed = 10%, pressed on an already tinted
>   fill = 14%. Focus-visible = `0 0 0 2px var(--panel), 0 0 0 4px var(--accent)` on every interactive element; never
>   `outline: none` without a replacement.
> - **Single-choice controls** (segmented: Typical / Dry / Wet year, Low / Medium / High, Rule / Model) show the choice
>   with a raised white thumb (`--raised` + `--e1`) on a `--panel-2` track, not with green.
> - **Dark tokens** (native apps only, for now): panel `#171a15`, panel-2 `#20241d`, raised `#23281f`, ink `#ecebe3`,
>   muted `#a3a69a`, accent `#9fcb9b` (ink on it `#10260f`), container `#2b3f2b` / `#cfe6c9`, warn `#e0b04a`,
>   bad `#f08a7a`. Data colours do not change.

## Edit 3: section 3, the contrast bullet

**Append to the end of the bullet that begins** "**Contrast:** body text >= 7:1 on its panel"

> Non-text boundaries that carry meaning (chip outline `#84877d`, check icon `#5f8a5c`, focus ring) are at least 3:1.
> Selected states never rely on colour alone: chips add a check icon, the current row adds a ring on its thumbnail, the
> active phone tab adds a pill.

## Edit 4: section 5, the status-word bullet

**Replace**

> - Live data carries no status word. Only example data (API not answering) is flagged, in words, not a pill: "Example numbers."
>   in italics, the warn colour and a small hatched square (hatching = "not measured" across the product, as on the season strips).

**With**

> - Live data carries no status word. Example data is flagged in words, not a pill: "Example numbers." in italics, the warn
>   colour and a small hatched square with 2px corners (`.status.example`); model estimates say "Estimated." in italics in
>   `--muted` with a dashed square (`.status.estimate`). Hatching = "not measured" across the product, as on the season
>   strips. When the whole server is down, one `.notice` (warn-container fill, 12px corners) says so once per panel.

## Edit 5: section 5c, phone

**Replace**

> Top bar = wordmark, field switcher, menu (date control and map layers inside). Sections become a bottom tab bar. The field panel
> is a bottom sheet over the map (peek, half, full via the grab handle). Wide sheets become full-screen pages between the bars, one
> column. Touch targets at least 44 px; nothing scrolls sideways except inside a table.

**With**

> Top bar = wordmark, field switcher, menu (date control and map layers inside). Sections become a bottom tab bar (64px;
> the active tab gets a 32px tonal pill behind its label). The field panel is a non-modal paper bottom sheet over a live
> map: 20px top corners, a 36x4 grey grabber (not a green bar), snap points peek 128px (name and facts), half 52% (plus a
> sideways row of action pills, primary first) and full; drag with fling, tap the grabber to cycle, 320ms snap. Wide
> sheets become full-screen pages between the bars, one column. Touch targets at least 44 px (visual 36-40px controls
> grow their hit area); nothing scrolls sideways except inside a table, the filter-chip row and the sheet's action row.

## Edit 6: section 6, the first bullet (shape)

**Replace**

> - Solid panels (`--panel`), 1px rules, radius 2-4px, one modest shadow. No blur/glass.

**With**

> - Solid panels (`--panel`), no blur/glass, no border on floating panels (the shadow is the edge).
> - **Radius scale** (tokens `--r-*`): 4 strips, swatches, status squares (2-3); 8 thumbnails, event rows, tooltips;
>   12 cards, list rows, the More detail row, notices, menu items; 16 floating panels, popovers, menus; 20 the phone
>   sheet's top corners; full (pill) for buttons, chips, segmented controls, the search field, icon buttons and the phone
>   tab indicator. Square (0-2px) stays for map label boxes, field-selection ticks, data cells and the printable brief.
>   Rule of thumb: rounded where the grower touches, crisp where they read.
> - **Elevation** (tokens `--e*`, shadow colour = ink, never pure black): `--e1` the one card per screen and the
>   segmented thumb; `--e2` a panel over the map; `--e3` menus and pickers; `--e-sheet` the phone sheet; `--e-stuck` a
>   sticky header or footer once content scrolls under it.
> - **Separation:** sections are separated by 24px of space, not by rules. Hairlines (ink 14%) only between answer rows,
>   fact rows and list rows where the eye tracks across. No 2px ink rules in panels, no dashed boxes.

## Edit 7: section 6, the "Actions" bullet

**Replace**

> - Actions: full-width rows with a title only (no subtitle); one primary per panel
>   (the printable summary). Chevron at the right only for things that open a view.

**With**

> - **Buttons** are pills, 44px tall (36px "small" with a 44px hit area), label 16px Libre Franklin 600, sentence case,
>   the grower's words. Four kinds only: primary (filled green, one per panel: "Print for your adviser"), secondary
>   (tonal green: the other next steps), outline (neutral: "Back to today", "Show all"), text (green text: "Sources",
>   "Look under the field in 3D", "What's this?"). Icon buttons are 40px circles with a faint ink disc (close, play). An
>   icon is 18-20px and sits before a label, never stacked above it.
> - **Next steps** in the field panel sit in a fixed footer as pills that wrap to two rows at 460px: "What's likely this
>   winter", "This field's year", "Compare rotations", then the primary "Print for your adviser". On a phone they are one
>   sideways-scrolling pill row under the sheet header.
> - **Filter chips** are 36px pills with a 1px outline; selected = tonal fill + leading check icon, never solid green.
>   Counts stay on the same line in a lighter weight.
> - **List rows** (pick list, events) are 12px-corner rows with a flat ink hover; the current field gets the tonal fill
>   and a ring on its thumbnail. No lift-on-hover, no shadows on rows. Chevron at the right only for things that open a view.
> - **Panel header** is paper, not green: field name (heading face, 28px; 22px on a phone), close icon button, one facts
>   line, one id line. Once the content scrolls it compresses to one 20px line with a soft edge.
> - **More detail** is a full-width 12px-corner row on `--panel-2` with the label in green, the three-word teaser in
>   muted text and a chevron that turns when open.
> - **Motion:** 120ms for hover and press, 180ms for selection (chip check, segmented thumb, chevron), 240ms for the
>   header compress and detail fade, 320ms for panel entry and sheet snaps; easing `cubic-bezier(0.2,0,0,1)` (enter
>   `cubic-bezier(0.05,0.7,0.1,1)`). Animate opacity, transform, colour and shadow only; respect reduced motion.

## Edit 8: section 7, item 10

**Replace**

> 10. Cards inside cards; side-stripe accent cards; 24px+ radii on small boxes.

**With**

> 10. Cards inside cards; side-stripe accent cards; 24px+ radii on boxes (pills on buttons and chips are fine); solid
>     brand-colour fills as a selected state; square 2px buttons and chips; controls with no hover, pressed or focus state.

## Edit 9: "Where things are"

**Append**

> - Tokens and component CSS for the rounded controls, with every state: `ui-research/mock/tokens.css` and
>   `ui-research/mock/components.css` (copied into `styles.css`); spec and reasons: `ui-research/REDESIGN.md`.
> - Native mapping (Compose `colorScheme` roles, `Shapes`, SwiftUI assets, sheet detents): `REDESIGN.md` section 3.8.

## Also update `references.md`

Add a section "Controls and selection states (Nov 2026)" with the sources in `REDESIGN.md` section 9: Material 3 token
files (chip, segmented, button, bottom sheet, state layers, motion), Apple HIG (44pt, sheet detents), Radix Themes and
shadcn/ui (tonal or neutral selection, raised segmented thumb), Linear's refresh post, Google Places UI Kit widths.
