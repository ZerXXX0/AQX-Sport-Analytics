---
name: ClutchIQ Precision Analytics
colors:
  surface: '#0c1322'
  surface-dim: '#0c1322'
  surface-bright: '#323949'
  surface-container-lowest: '#070e1d'
  surface-container-low: '#141b2b'
  surface-container: '#191f2f'
  surface-container-high: '#232a3a'
  surface-container-highest: '#2e3545'
  on-surface: '#dce2f7'
  on-surface-variant: '#e1bfb5'
  inverse-surface: '#dce2f7'
  inverse-on-surface: '#293040'
  outline: '#a98a80'
  outline-variant: '#594139'
  surface-tint: '#ffb59d'
  primary: '#ffb59d'
  on-primary: '#5d1900'
  primary-container: '#ff6b35'
  on-primary-container: '#5f1900'
  inverse-primary: '#ab3500'
  secondary: '#41eec2'
  on-secondary: '#00382b'
  secondary-container: '#00d1a7'
  on-secondary-container: '#005441'
  tertiary: '#ffb3ad'
  on-tertiary: '#68000a'
  tertiary-container: '#ff6862'
  on-tertiary-container: '#6b000b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59d'
  on-primary-fixed: '#390c00'
  on-primary-fixed-variant: '#832600'
  secondary-fixed: '#55fcd0'
  secondary-fixed-dim: '#28dfb5'
  on-secondary-fixed: '#002118'
  on-secondary-fixed-variant: '#00513f'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#0c1322'
  on-background: '#dce2f7'
  surface-variant: '#2e3545'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.05em
  metric-display:
    fontFamily: JetBrains Mono
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system embodies high-frequency sports intelligence: the analytical density of a Bloomberg Terminal distilled through the broadcast polish of elite sports media. Tailored for front-office analysts, scouting directors, betting quants, and serious basketball enthusiasts, the interface conveys absolute authority, precision, and operational velocity.

The aesthetic fuses **Modern High-Density Technical UI** with **Tactical High-Contrast Data Display**:
- Deep navy space anchors the visual hierarchy, eliminating cognitive fatigue during intensive data parsing.
- Precise luminous accents (Electric Orange and Neon Teal) direct immediate ocular attention toward decisive indicators, clutch efficiency splits, and hot zones.
- Surface architecture relies on crisp mechanical boundaries, structural dividers, and micro-luminance rather than heavy dropped shadows. Every pixel communicates statistical value.

## Colors

The palette leverages calibrated optical contrast on an ultra-deep canvas to balance data density with immediate glanceability.

### Background & Surface Hierarchy
- **Canvas Base (`#0A0F1E`)**: Ultra-deep navy foundation providing total immersion.
- **Sidebar Surface (`#0D1321`)**: Grounded low-sheen navigation tier separating filters from the operational dashboard.
- **Panel & Card Surface (`#111827`)**: Base level for analytics widgets, shot charts, and data tables.
- **Surface Elevated / Alternating Striping (`#161D2E`)**: Subtle secondary fill for alternating zebra rows, nested containers, and hover states.
- **Structural Stroke (`#1F2937`)**: Crisp boundary definition for cards, split-views, and court vectors.

### Accent & Functional Semantics
- **Electric Orange (`#FF6B35`)**: Primary telemetry driver used for high-impact CTAs, active tab indicators, range-slider thumbs, clutch-time filters, and left-edge card accents.
- **Neon Teal (`#00D4AA`)**: Quantitative positive indicators, made shot vectors, true shooting percentage over-indexing, and efficiency peaks.
- **Missed / Inefficient Indicator (`#374151` base, `#EF4444` threshold)**: Off-target shots rendered in muted slate with sharp crimson reserved exclusively for catastrophic turnover or shooting regressions.
- **Text Primary (`#F9FAFB`)**: High-contrast, optical white for primary data readouts, labels, and headlines.
- **Text Secondary (`#9CA3AF`)**: Balanced silver-gray for secondary metrics, column headers, and timestamps.
- **Text Muted (`#6B7280`)**: De-emphasized metadata, league-average benchmarks, and baseline shot coordinates.

## Typography

Typography delivers immediate scannability across dense data layouts. **Inter** powers executive readability across headlines, body copy, and UI controls with tight vertical proportions and robust character shaping. **JetBrains Mono** governs statistical values, spatial coordinate displays, shot clocks, advanced metrics (eFG%, TS%, RAPTOR), and table grids.

### Implementation Directives
- **Tabular Figures**: Force `font-variant-numeric: tabular-nums lining-nums` across all numeric expressions, regardless of font family, ensuring table alignment remains steady during real-time data streaming.
- **Metric Micro-Headers**: Set all chart titles, table sort keys, and metric badges in uppercase `label-sm` or `label-md` with `letter-spacing: 0.05em` for analytical structure.
- **Data Densification**: Body text defaults to `body-md` (13px) to maximize screen economy without sacrificing legibility under prolonged viewing conditions.

## Layout & Spacing

The layout is structured around an ultra-dense, multi-pane workbench layout optimized for widescreen displays (1440px+) while retaining fluid responsiveness down to standard laptop and mobile viewports.

### Architectural Blueprint
- **Global Structure**: Persistent Left Utility Dock (width: 280px fixed), Global Fixed Command Header (height: 56px), and a fluid multi-column workspace.
- **Grid Layout**: A 12-column adaptive CSS grid with `1rem` (16px) gutters and `1.5rem` (24px) container margins. 
- **Analytical Pane Division**:
  - Primary Visualizer Zone: Spans 7 or 8 columns (Half-Court Shot Charts, Heat Maps).
  - Telemetry Stream: Spans 4 or 5 columns (Deep Breakdown Tables, Shot Distributions, Clutch Calibration Curves).
- **Responsive Adaptations**:
  - Below 1024px (Tablet): Persistent sidebar folds into an off-canvas drawer; main workspace transitions into a 6-column reflow stacking chart above data telemetry.
  - Below 640px (Mobile): Outer margin drops to `1rem` with `0.75rem` gutters. Metric cards stack single-file; data tables introduce horizontal scroll with sticky primary column pinning.

## Elevation & Depth

This design system avoids high-blur drop shadows, using structured dark-mode depth achieved through **luminescent boundary layers, deliberate surface luminance shifts, and selective edge glows**.

### Depth Layers
- **Ground Floor (`#0A0F1E`)**: Canvas baseline for app-level framing and court backdrop.
- **Tier 1 (`#0D1321`)**: Navigation rail and filter drawer, framed with a 1px border (`#1F2937`) on its right edge.
- **Tier 2 (`#111827`)**: Base cards, analytics widgets, court frames, and master table wrappers. Boundary: 1px continuous solid `#1F2937`.
- **Tier 3 (`#161D2E`)**: Dropdown panels, nested flyouts, tooltips, and floating hover inspect cards.

### Luminous Depth & Accent Glow
- **Metric Cards**: Anchored with a solid 3px left border (`#FF6B35`). On hover, an ambient accent aura appears: `box-shadow: 0 0 20px -4px rgba(255, 107, 53, 0.15)`.
- **Interactive Active Focus**: Active inputs, focused tabs, and range thumbs emit a constrained neon radiance: `0 0 10px rgba(255, 107, 53, 0.35)`. Positive status badges utilize a teal equivalent: `0 0 8px rgba(0, 212, 170, 0.25)`.

## Shapes

The design system embraces a **Soft-Mechanical Geometry** (`roundedness: 1`), conveying engineering rigor and analytical seriousness.

### Radii Allocation
- **Containers, Cards & Data Tables**: `0.25rem` (4px). Clean, crisp corners eliminate wasted quadrant space and maximize chart real estate.
- **Form Controls, Search Inputs & Filter Chips**: `0.25rem` (4px) to retain structural continuity with parent cards.
- **Badges, Status Tags & Shot Chart Nodes**: Micro-pills use full circular rounding (`9999px`) to create clear differentiation between data markers and layout containers.

## Components

### 1. Metric Cards
- **Base Style**: Background `#111827`, border 1px solid `#1F2937`, 3px solid `#FF6B35` left accent strip. Padding: `space-lg`.
- **Content Hierarchy**: Top row displays category label in `label-sm` (uppercase `#9CA3AF`) and a status pill. The middle tier features `metric-display` (`#F9FAFB`), followed by micro-trend deltas (+3.8% eFG vs. League Average) colored in `#00D4AA` (positive) or `#EF4444` (negative).
- **Interactive State**: Border transitions to `#374151` with a localized Electric Orange ambient edge glow on hover.

### 2. Navigation Tabs (6-Tab Primary Bar)
- **Geometry**: Horizontal strip anchored to page headers. Border-bottom: 1px solid `#1F2937`.
- **Item States**: Text set in `body-md` (medium weight). Inactive items rendered in `#9CA3AF`. Active state rendered in `#F9FAFB` with a continuous 2px bottom border in `#FF6B35` positioned flush with the baseline.
- **Active Badges**: Quantitative count pill placed right of label; inactive: `#161D2E` background with `#9CA3AF` text; active: `#FF6B35` with `#0A0F1E` text.

### 3. Persistent Sidebar & Filter Inputs
- **Sidebar Framing**: Full viewport height, width 280px, background `#0D1321`, right border 1px solid `#1F2937`.
- **Filter Select Controls**: Background `#111827`, border 1px solid `#1F2937`, text `body-md` `#F9FAFB`, right custom caret in `#9CA3AF`. On focus: border becomes `#FF6B35` with a subtle orange glow.
- **Range Sliders**: Track height 4px, background `#1F2937` with filled track section in `#FF6B35`. Thumb diameter 14px, solid `#FF6B35`, border 2px solid `#0A0F1E`, emitting an orange glow when dragged.

### 4. Custom Data Tables
- **Container**: Card wrapper with sticky `thead`.
- **Headers**: Background `#111827`, text `label-sm` (uppercase `#9CA3AF`), border-bottom 2px solid `#1F2937`, padding `0.5rem 1rem`. Includes sort direction indicators.
- **Row Striping**: Alternating zebra striping: odd rows `#111827`, even rows `#161D2E`.
- **Row Interactions**: Hover shifts row background to `#1F2937` with transition speed 100ms.
- **Numeric Cells**: Styled in `JetBrains Mono` (`label-md`), right-aligned. Negative and positive split deltas highlighted respectively in `#EF4444` and `#00D4AA`.

### 5. Half-Court Shot Visualization
- **Court Vectoring**: Vector lines drawn in 1px stroke `#1F2937` over `#0A0F1E` court surface.
- **Made Shot Nodes**: 6px circular dot, fill `#00D4AA`, stroke 1px `#0A0F1E`, shadow `0 0 6px rgba(0, 212, 170, 0.4)`.
- **Missed Shot Nodes**: 6px 'X' marker or muted outline node in `#4B5563`.
- **Zone Heatmaps**: Low-opacity radial polygonal fills (Teal for >50th percentile, Orange for high volume, Dark Slate for neutral/cold).

### 6. Interactive Controls (Buttons & Toggles)
- **Primary Action**: Background `#FF6B35`, text `#0A0F1E` (semi-bold 600), radius 4px. Hover: brightness 1.1 with `0 0 12px rgba(255, 107, 53, 0.4)`.
- **Secondary Action**: Background `#161D2E`, border 1px solid `#1F2937`, text `#F9FAFB`. Hover: border `#9CA3AF`.
- **Checkboxes & Radios**: 16x16px, background `#0A0F1E`, border 1px solid `#374151`. Checked: fill `#FF6B35` with check glyph in `#0A0F1E`.