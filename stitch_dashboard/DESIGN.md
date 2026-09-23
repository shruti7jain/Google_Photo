---
name: Discovery Engine Design System
colors:
  surface: '#f8faf7'
  surface-dim: '#d8dbd8'
  surface-bright: '#f8faf7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f1'
  surface-container: '#eceeec'
  surface-container-high: '#e7e9e6'
  surface-container-highest: '#e1e3e0'
  on-surface: '#191c1b'
  on-surface-variant: '#424654'
  inverse-surface: '#2e3130'
  inverse-on-surface: '#eff1ef'
  outline: '#737785'
  outline-variant: '#c3c6d6'
  surface-tint: '#0856cf'
  primary: '#0041a2'
  on-primary: '#ffffff'
  primary-container: '#0b57d0'
  on-primary-container: '#ced9ff'
  inverse-primary: '#b2c5ff'
  secondary: '#00639b'
  on-secondary: '#ffffff'
  secondary-container: '#7ec1ff'
  on-secondary-container: '#004f7d'
  tertiary: '#00541e'
  on-tertiary: '#ffffff'
  tertiary-container: '#006f2a'
  on-tertiary-container: '#87f194'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001847'
  on-primary-fixed-variant: '#0040a1'
  secondary-fixed: '#cee5ff'
  secondary-fixed-dim: '#96cbff'
  on-secondary-fixed: '#001d33'
  on-secondary-fixed-variant: '#004a76'
  tertiary-fixed: '#8ffa9b'
  tertiary-fixed-dim: '#73dc82'
  on-tertiary-fixed: '#002108'
  on-tertiary-fixed-variant: '#00531e'
  background: '#f8faf7'
  on-background: '#191c1b'
  surface-variant: '#e1e3e0'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 26px
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  title-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system establishes a high-utility, systematic visual language tailored for internal product management and engineering operations within the Google Photos Discovery Engine ecosystem. The tone is utilitarian, calm, hyper-organized, and distinctly modern Google Enterprise.

The interface emphasizes content-first navigation, operational velocity, and high data density without cognitive overload. It bridges the consumer refinement of Google Photos with the structured rigor of Google Cloud Console. Visual clutter is stripped away in favor of purposeful whitespace, clear surface-tier differentiation, crisp geometric structuring, and standardized feedback loops.

## Colors
The palette follows the tonal mechanics of Material Design 3, rooted in core Google identity tokens:

- **Primary (`#0b57d0`):** Core interactive states, active navigation indicators, key metrics, and primary action buttons.
- **Secondary (`#00639b`):** Data filtering states, secondary action triggers, and analytics sub-groupings.
- **Tertiary (`#1e8e3e`):** Model health telemetry, pipeline readiness confirmations, and operational successes.
- **Surface Hierarchy:** 
  - `surface-lowest`: `#ffffff` (Card content backgrounds, high-contrast focal points)
  - `surface`: `#f8fafd` (Primary viewport canvas)
  - `surface-container`: `#f1f3f4` (Side rails, filter bars, control toolbars)
  - `surface-container-high`: `#e9eef6` (Hover states, table headers, pinned panels)
- **Outline & Borders:** `#e0e3e7` for interior card dividers and structural boundaries; `#dadce0` for component edge outlines and inputs.
- **Text & On-Surface:** `#1f1f1f` for primary legibility, `#444746` for secondary metadata, and `#747775` for passive labels and placeholders.

## Typography
Plus Jakarta Sans serves as the primary face to deliver the clean, geometric humanist characteristics emblematic of Google Sans.

- Numeric figures across metrics displays and data grids must use tabular lining where applicable.
- Header levels 1 through 3 employ medium to semi-bold weights with slight negative letter tracking to retain balance at large scales.
- All body copies use normal weight for scanning ease across high-density query tables and cluster graphs.
- Functional labels and metadata counters strictly consume the `label-*` tiers with calibrated positive tracking for clarity against container backgrounds.

## Layout & Spacing
The layout adheres to an adaptive, responsive 12-column fluid grid system pinned against a 256px persistent collapsible navigation rail:

- **Desktop (1440px+):** 12 columns, 24px gutters (`gutter-lg`), 32px canvas margins (`margin-lg`). Accommodates multi-pane query builders, side-by-side clustering diagnostics, and telemetry logs.
- **Compact Desktop / Tablet Landscape (1024px–1439px):** 12 columns, 16px gutters (`gutter`), 24px canvas margins (`margin-md`). Auxiliary panels fold into flyouts or sheet overlays.
- **Tablet Portrait & Mobile (Below 1024px):** 4 to 8 columns, 16px gutters, 16px margins (`margin`). Navigation rail transforms into a modal navigation drawer; tabular clusters stack into discrete cards.

Horizontal and vertical rhythm follows a strict 4px base increment, with internal component padding standardized on 8px (`space-sm`) and 16px (`space-md`).

## Elevation & Depth
Depth adheres to Material Design 3 surface-tonal elevation rather than harsh, dramatic drop shadows.

- **Level 0 (Flat):** `surface` background (`#f8fafd`), zero shadow, zero boundary outlines. Used exclusively for page canvases.
- **Level 1 (Cards & Modules):** Raised via low-contrast structural outlines (`1px solid #e0e3e7`) on `#ffffff` surfaces. Used for dashboard cards, analytics widgets, and list containers.
- **Level 2 (Hover & Active Surfaces):** Micro ambient blur: `box-shadow: 0 1px 3px 0 rgba(60, 64, 67, 0.15), 0 4px 8px 3px rgba(60, 64, 67, 0.05)`.
- **Level 3 (Dropdowns & Popovers):** Soft diffused drop: `box-shadow: 0 2px 6px 2px rgba(60, 64, 67, 0.15), 0 8px 16px 4px rgba(60, 64, 67, 0.08)` paired with a `#dadce0` border.
- **Level 4 (Drawers & Modals):** Elevation tier 4 with backdrop protection (`rgba(31, 31, 31, 0.32)` scrim) and elevation shadow: `box-shadow: 0 8px 24px 6px rgba(60, 64, 67, 0.20)`.

## Shapes
The design system combines distinct M3 geometric curves:
- **Dashboard Modules & Data Cards:** Fixed at `16px` border-radius (`rounded-2xl` equivalent) for an approachable, polished Google product feel.
- **Chips, Badges & Interactive Tags:** Full pill radius (`9999px`).
- **Text Inputs, Buttons & Select Fields:** Standardized at `8px` (`0.5rem`) for professional, dense form alignment.
- **Floating Action Trays & Toolbars:** Standardized at `12px` to bridge cards and smaller interactive elements.

## Components

### Buttons
- **Filled (Primary):** Solid `#0b57d0` fill, `#ffffff` text, 8px border radius, 36px height (compact enterprise sizing). Hover shifts to `#0842a0`.
- **Tonal (Secondary):** Surface `#d3e3fd` fill, `#041e49` text. Hover transitions to `#c2d7fc`.
- **Outlined:** `1px solid #dadce0`, transparent background, `#0b57d0` text. Hover adds a 4% primary tint overlay (`#0b57d00a`).
- **Text:** Transparent background, `#0b57d0` text, 8px hover padding.

### Chips (Pill-Shaped)
- Radius is strictly full pill (`9999px`).
- Height is 32px with 12px horizontal padding.
- **Filter Chips:** `#f1f3f4` background with a `#747775` border. Selected state switches to `#d3e3fd` fill, no border, with a 16px leading checkmark icon and `#041e49` label.
- **Status Badges:** Compact 24px height, light pastel fills with high-contrast text (e.g., `#e6f4ea` background with `#137333` text for active ML discovery indexes).

### Cards & Data Panels
- Background: `#ffffff`.
- Border: `1px solid #e0e3e7`.
- Radius: `16px` (`rounded-2xl`).
- Padding: 20px internally. Headers contain a 40px height flex row with title in `title-md` and contextual action menus pinned to the right.

### Input Fields & Search Bars
- **Global Discovery Query Bar:** Persistent 48px height, 24px pill radius, `#e9eef6` background, inset search icon, `#444746` placeholder. Focus triggers `#ffffff` background with level-2 elevation and `#0b57d0` outline.
- **Form Fields:** Height 40px, 8px border radius, `1px solid #dadce0`, `#ffffff` fill. Active focus applies `2px solid #0b57d0` with label transition.

### Checkboxes & Radio Controls
- Checkboxes: 18x18px box, 2px border radius. Unselected uses `#444746` border; selected uses `#0b57d0` fill with white checkmark.
- Radio buttons: 18px circle, `#0b57d0` active inner dot (8px diameter).

### Discovery Engine Domain-Specific Components
- **Cluster Visualizer Nodes:** Interactive cards with 12px radius, micro image thumbnail grids (4x4 matrix), and confidence score pills.
- **Pipeline Metric Bar:** Horizontal segmented status bar showing latency, model version (`gemini-vision-v2`), and real-time ingestion throughput with tertiary `#1e8e3e` indicators.