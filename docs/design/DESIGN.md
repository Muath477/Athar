# Athar design contract: «حاشية المخطوط» (Manuscript Margin)

This file is the theme lock for the Athar web app. Every screen is built from the tokens and primitives listed here. A change to a token value, a new hue, a new font or a new radius is a change to this contract first.

## Essence

- Essence: عميق · متأنٍ · علمي (deep, unhurried, scholarly).
- Adjectives and what each one means on screen:
  - عميق: warm paper ground, dark iron-gall ink, generous Arabic line height, no decoration that does not carry information.
  - متأنٍ: one primary action per view, confirmations for anything irreversible, slow-reading type sizes rather than dense UI type.
  - علمي: ruled tables, tabular Arabic-Indic numerals, every specialist judgement attributed and dated.
- Proposition: the wall is the text; the specialist writes in its margin.
- Mode per surface: dashboard, maps, review, condition = Operate. Visitor pages (home, capture, site, passport) = Experience with Operate controls. PDF report = Read.

## Direction

- Source system: the margins of Arabic manuscripts. The متن (main text) sits in a ruled block in the middle; حواشٍ (marginal glosses) and rubrics in red ink sit beside it; the page is framed by a جدول, a thin ruled border in gold and red.
- Default it refuses: popup windows for comments and notes. A note about a wall is never a modal, a toast or a tooltip; it is written next to the thing it is about, and stays there.
- Signature move: **الحاشية**. Specialist notes, field-inspection notes, analysis summaries, low-confidence warnings and pending-draft notices render as a marginal note: a 2px rubric line on the inline-start side, a short red label (حاشية، حاشية المختص، حاشية التحليل، حاشية: ثقة منخفضة) and the note in ink. Component: `src/components/brand/margin-note.tsx`. The rubric line is the only coloured side border in the product, and the lint rule against side accent borders (R2) is waived for it by this contract.
- Second identity move: the ruled header. The site header sits on paper (`white` = `#FBF4E4`) and is closed by the `.jadwal` rule: a 1px gold line over a 2px rubric line. It replaces the old Sadu band.
- Risk and its guard: red is both the brand rubric and the colour people read as danger. Guarded by the semantic rule below.

## Semantic rule: urgent is never colour alone

The rubric red (`sadu`, `#9E2A2B`) is the voice of the specialist: primary actions, marginal notes, active navigation. Urgency is a state of the wall, not a voice, so:

1. `urgent` has its own deeper red, `#7A1C1E` (oxblood), instead of reusing the rubric. A primary button and an urgent count must not look like the same thing. The two reds differ by only 1.40:1, which is why the next rule exists.
2. Every urgent signal carries a text label **and** an icon (`TriangleAlertIcon`, lucide). Use `SeverityLabel` (`src/components/brand/severity-label.tsx`) for severities; urgent counts show the icon beside the number. Colour is the third channel, never the only one.
3. A low-confidence or "needs review" message is a margin note in rubric red, not urgent red: it asks for the specialist's attention, it does not describe damage.

## Type

- Arabic, display and body: **Scheherazade New** (SIL, OFL), weights 400 and 700, Arabic subset. Chosen for the manuscript source: it is a Naskh designed for long reading, close to the hand of the margins.
- Latin: **Cormorant Garamond** (OFL), weights 500 and 700. 400 is too thin at UI sizes, so 500 is the regular weight. It also renders spaces, Latin punctuation, emails, codes (`E1`, `D3`) and `<kbd>`.
- Both are self-hosted from `src/app/fonts/` with `next/font/local` (licences beside the files). Google Fonts is not used at build time so the build works offline and in Docker. Stack: `--font-sans: Scheherazade New, Cormorant Garamond, Noto Naskh Arabic, Geeza Pro, serif`; `.font-latin` for Latin-only strings.
- Scheherazade renders small for its em, so the Tailwind scale is raised and keeps its names:

| Token | Size | Line height | Use |
|---|---|---|---|
| `text-xs` | 14px | 1.7 | captions, helper text |
| `text-sm` | 16px | 1.75 | controls, table cells, nav |
| `text-base` | 18px | 1.8 | body (set on `body`) |
| `text-lg` | 21px | 1.6 | section headings |
| `text-xl` | 25px | 1.45 | dialog titles |
| `text-2xl` | 30px | 1.4 | stat values, page sections |
| `text-3xl` | 38px | 1.35 | page titles |
| `text-4xl` | 46px | 1.3 | visitor display |

- Ratio about 1.2 (dense tool). Display 46 / body 18 = 2.56×. Headings line height 1.35 and `text-wrap: balance`.
- No letter-spacing and no italic on Arabic. Weights: 400 body, 700 headings and primary actions. Nothing in between.
- Numerals: Arabic-Indic everywhere via `toLocaleString("ar-SA")`, tabular in tables (`table { font-variant-numeric: tabular-nums }`).

## Colour

Light only. The identity is paper and ink, and the main field use is outdoors in daylight; a dark mode is not shipped. If one is added later it is designed, not inverted: ground `oklch(20% 0.02 60)` (lamp-lit leather), ink `oklch(92% 0.025 85)`, rubric lifted to `oklch(64% 0.15 25)`, and every pair below re-checked.

Token names are kept from the first theme so existing code keeps working; only values changed.

| Token | Role | Hex | OKLCH |
|---|---|---|---|
| `sand` / `--background` | page ground | `#F5ECD7` | oklch(94.5% 0.029 87.5) |
| `white`, `surface` / `--card`, `--popover` | paper surface (pure white is not used) | `#FBF4E4` | oklch(96.8% 0.022 87.2) |
| `clay`, `line` / `--border` | ruling, hairlines, skeleton | `#D9C7A3` | oklch(83.5% 0.052 84.5) |
| `mud` / `--muted-foreground`, `--input` | secondary text, input borders | `#6E5640` | oklch(47.2% 0.046 63.9) |
| `ink` / `--foreground` | text, inverse surfaces | `#2B1D12` | oklch(24.5% 0.029 59.0) |
| `sadu` / `--primary`, `--ring` | rubric red: primary action, notes, focus | `#9E2A2B` | oklch(46.8% 0.152 24.9) |
| `on-accent` / `--primary-foreground` | text on red, gold, ochre | `#FFF8EC` | oklch(98.1% 0.018 81.3) |
| `watch` | gold accent2, "watch" severity | `#7E6026` | oklch(50.8% 0.084 81.2) |
| `moderate` | ochre, "moderate" severity | `#8A5E14` | oklch(51.7% 0.102 74.4) |
| `urgent` / `--destructive` | oxblood, urgent and destructive | `#7A1C1E` | oklch(38.5% 0.128 24.6) |
| `wall` | mud-brick illustration fill | `#C9A87A` | oklch(75.0% 0.073 75.5) |
| `--muted`, `--accent` | hover and quiet fills | `color-mix(in oklab, line 45–55%, sand)` | derived |

Adjusted from the identity board: gold `#8A6A2C` → `#7E6026` and ochre `#9A6A1C` → `#8A5E14`, because the board values reach only 4.27:1 and 4.01:1 on the ground and both are used as text. Urgent `#9E2A2B` → `#7A1C1E` for the reason in the semantic rule. The app icon uses the same adjusted gold.

Proportion: ground and paper about 60%, ink and mud about 30%, rubric red under 10% (one primary action, active nav, notes). Gold appears in the mark, the jadwal and watch badges only.

### Contrast (WCAG 2.2, computed)

Text needs 4.5:1, UI boundaries 3:1. Every pair used in the product:

| Foreground | Background | Ratio | Use |
|---|---|---|---|
| ink `#2B1D12` | sand `#F5ECD7` | 13.88 | body text |
| ink `#2B1D12` | paper `#FBF4E4` | 14.89 | text on surfaces |
| mud `#6E5640` | sand `#F5ECD7` | 5.82 | secondary text |
| mud `#6E5640` | paper `#FBF4E4` | 6.25 | secondary text, input border (UI) |
| sadu `#9E2A2B` | sand `#F5ECD7` | 6.33 | notes, links, active nav, focus ring (UI) |
| sadu `#9E2A2B` | paper `#FBF4E4` | 6.80 | notes on surfaces, focus ring (UI) |
| on-accent `#FFF8EC` | sadu `#9E2A2B` | 7.05 | primary button |
| sand `#F5ECD7` | sadu `#9E2A2B` | 6.33 | legacy `text-sand` on red |
| watch `#7E6026` | sand `#F5ECD7` | 4.98 | gold text |
| watch `#7E6026` | paper `#FBF4E4` | 5.34 | gold text |
| on-accent `#FFF8EC` | watch `#7E6026` | 5.54 | watch badge |
| moderate `#8A5E14` | sand `#F5ECD7` | 4.84 | ochre text |
| moderate `#8A5E14` | paper `#FBF4E4` | 5.19 | ochre text |
| on-accent `#FFF8EC` | moderate `#8A5E14` | 5.39 | moderate badge |
| urgent `#7A1C1E` | sand `#F5ECD7` | 8.88 | urgent text, errors |
| urgent `#7A1C1E` | paper `#FBF4E4` | 9.52 | urgent text on surfaces |
| on-accent `#FFF8EC` | urgent `#7A1C1E` | 9.88 | urgent badge, destructive button |
| sand `#F5ECD7` | ink `#2B1D12` | 13.88 | inverse panels, selected segment |
| sand `#F5ECD7` | mud `#6E5640` | 5.82 | legacy `bg-mud text-sand` buttons |
| ink `#2B1D12` | clay `#D9C7A3` | 9.83 | text on ruled fills |
| ink `#2B1D12` | wall `#C9A87A` | 7.28 | labels on wall illustrations |
| clay `#D9C7A3` | sand `#F5ECD7` | 1.41 | decorative ruling only, never a control boundary |
| urgent `#7A1C1E` | sadu `#9E2A2B` | 1.40 | why urgent needs label + icon |

Control boundaries use `mud` (inputs, checkboxes, radios) or `ink` (outline buttons), never `clay`. Disabled controls are exempt and drop to 45% opacity.

## Space

- Base unit 4px (Tailwind default). Inside a group: 4–8px (`gap-1`…`gap-2`). Between fields: 12–16px. Between page sections: 20–24px (`gap-5`, `gap-6`).
- Content column `max-w-5xl` with 16px gutters. The editor is a متن + حاشية grid: main column 3fr, margin column `minmax(16rem, 1fr)` holding the glossary, field review and notes.
- Touch targets: every control is at least 44px tall (`min-h-11` is built into `Button`, `Input`, `NativeSelect`, `SelectTrigger`, `TabsTrigger`, menu items).

## Shape and elevation

- Two radius values: **2px** for everything rectangular (panels, buttons, inputs, badges, dialogs) and **full** for dots, avatars and radio indicators. Tailwind `rounded-sm` … `rounded-3xl` all resolve to 2px, so older `rounded-xl` panels follow automatically. Pill buttons are retired; use `Button`.
- Elevation is the edge, not the shadow: surfaces are paper (`bg-white`) with a 1px `line` border. Overlays get an ink scrim (`bg-ink/45`). No element combines a border with a soft shadow; no `shadow-*` in primitives.

## Motion

- Tokens: 150ms for colour and hover, 200ms for dialogs, 200–250ms for sheets; easing `--ease-quill: cubic-bezier(0.2, 0.7, 0.2, 1)`.
- Allowed to move: dialogs and menus (fade and 95% zoom from origin), sheets (slide from their edge), skeleton pulse while loading, progress width. Nothing animates on page load.
- `prefers-reduced-motion` turns animations and transitions to 1ms globally.

## Icons and imagery

- One set: lucide-react, default 2px stroke, 16–20px. Directional icons mirror in RTL (the submenu chevron points to the inline end); non-directional icons (alert triangle, check, logos) never mirror.
- The mark (`src/components/brand/athar-mark.tsx`, `public/icon.svg`, `src/app/icon.svg`): a framed page with three ruled lines, a rubric bracket in the margin and a gold dot. It is not mirrored in RTL.
- Imagery is real: the wall photos the user takes, satellite tiles, the 3D site model. No stock photos, no illustration, no Islamic geometric pattern or mashrabiya used as texture.

## Components

- Primitives live in `src/components/ui/` (shadcn/ui, new-york source rewritten for this contract: logical properties only, 2px radius, 44px targets, Arabic copy such as «أغلق»). Add new ones in the same style; do not import shadcn defaults unchanged.
- `Button` variants: `default` (rubric, one per view), `outline` (ink border, secondary), `secondary` (paper), `ghost`, `segment` (toggle groups using `aria-pressed` or `aria-checked`), `destructive`, `destructive-outline`, `link`.
- Use `NativeSelect` for any select that is filled by tests or forms (`selectOption` needs a real `<select>`); `Select` (Radix) only for rich options.
- Confirm irreversible actions with `AlertDialog`; keep the action label a verb («اعتمد», «ألغِ التعديلات») and put the consequence in the description.
- Use `Card` sparingly and never inside another card; prefer a ruled section (`border-t border-line`) or a paper panel.
- RTL: `<html dir="rtl">` plus Radix `Direction.Provider dir="rtl"` in `src/components/providers.tsx`, so portalled menus, selects, dialogs and tabs get RTL keyboard handling and placement. Toasts (sonner) are configured `dir="rtl"` at the bottom-left, with the Arabic region label «الإشعارات».

## Constant vs variable

- Constant on every page: the paper header with the mark and the jadwal rule, the type scale, the two radii, rubric for the single primary action, margin notes for anything a person or the analysis wrote about a wall, label + icon for urgency, Arabic-Indic numerals.
- May flex per page: layout (single column, متن + حاشية grid, tables), density, whether the page has a primary action at all, illustration of the wall with `wall` and the damage palette (`src/lib/damage-palette.ts`, a data palette outside this contract's brand colours).
