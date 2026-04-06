# GRAPHICAL STYLE — COMPACT REF
USG ideology (Neil Panchal). Density target: cockpit / Bloomberg / mission control.

## PHILOSOPHY
Every pixel carries data. 40+ readouts visible simultaneously. Zero ornamentation. Overwhelming for 5s, legible forever. Dense not sparse. Flat not hierarchical. Timeless not fashionable. Don't infantilize users.

## TENETS
- DENSITY: No decorative headers/heroes/branding displacing content. Whitespace structural only. Remove padding to fit more rows.
- SIMULTANEITY: No tabs/accordions/truncation hiding displayable data. Scroll ok, hiding not. Never click to reveal.
- FUNCTIONALISM: Unadorned by design. Adornment reduces SNR.
- PERFORMANCE: Load/render/interaction latency are design metrics. No info gain → discard.
- DATASHEET: Zero-impedance access. Fully characterized data (ref: Analog Devices).
- TIMELESS: Correct in 2005 and 2035. Fashion = enemy of permanence.

## TYPE
Primary: monospaced. Berkeley Mono > JetBrains Mono > IBM Plex Mono > Courier Prime.
Secondary: Neue Haas Grotesk / Univers / Akzidenz-Grotesk. NEVER Inter/Roboto/Poppins/Space Grotesk.
Scale: 1.125 or 1.200 modular. No bold in body — use CAPS/letterspacing/color. Bold = headings only.
Tabular numerals everywhere. Prose min 14px. Dense data: 10–12px mono. Section labels: 8–9px uppercase letterspaced muted.

## COLOR (light|dark)
```
bg        #FFF|#0A0A0A    surface   #F5F5F5|#141414
text      #1A1A1A|#E5E5E5 muted     #6B6B6B|#808080
dim       #505050|#606060  border    #D4D4D4|#2A2A2A
subtle    #E8E8E8|#1A1A1A accent    #0057FF|#3B82F6
red       #DC2626          amber     #D97706
green     #16A34A          cyan      #06B6D4
```
No gradients/shadows. Dynamic light/dark mode via system preference (`prefers-color-scheme`). WCAG AAA body, AA minimum all text. Color = data channel (state/threshold/category), never decorative.

## LAYOUT
8px grid (4px sub-grid for cockpit density).
Spacing: 4/8/16/24/32px. Margins: 64px desktop, 16px mobile.
- Tables > cards. Lists > grids. Dense > spacious. Always.
- Multi-panel CSS grid: 3–4 cols, gap:1px, bg-color on container as dividers.
- KPI strip top: label(8px muted uppercase) → value(16–20px light) → subtext(8px dim). Padding 4–6px.
- Panel padding: 6–8px. Cell padding: 2–4px vert, 4–8px horiz.
- Status bar persistent: 24–28px, 10px font, system state + timestamps + connection.
- Prose max-width 720px. Data tables full-width. No max-width on data.
- Mobile: horizontal scroll > column hiding.

## COMPONENTS
TABLE: Primary unit. 2–4px/4–8px padding. Right-align numbers. Mono numerals. Headers 8px uppercase muted border-bottom. Row borders 1px subtle. Hover bg shift. Alt rows only >20.
INLINE VIZ: Dots(6–8px) for status, micro bars(14–32px) for ratios, gauge fills for capacity. Supplement values, never replace.
GAUGE: label(fixed,right,muted) → track(flex,8px,surface) → fill(threshold-colored) → limit(1px red) → value(fixed,right). 3px gap stack.
KPI: label(8px uppercase muted) → value(16–20px light tabular) → sub(8px dim). border-right dividers.
BUTTON: 0–2px radius. Uppercase mono. State via border/bg, not shadow/scale.
INPUT: Visible borders. Label above. No floating/placeholder labels. Mono for structured fields.
STATUS: Dots(6–8px) or text color. box-shadow glow for liveness. No icons for status. No toasts.
BADGE: 8px uppercase, 1px border, 1–4px pad. No fill, no radius.
NAV: Flat. Visible > hamburger. Mono labels.

## IMAGERY
Icons: functional only, text labels preferred. Lucide/Phosphor(light)/custom 24px SVG.
Images: documentation only. No stock/lifestyle/illustration except technical diagrams.
Charts: line/scatter. No 3D/shadows. Mono axes. Grid 0.1–0.2 opacity. Annotations > legends. Prefer inline sparklines in table cells.

## MOTION
State transitions only. Max 150ms ease-out. No bounce/spring/parallax/scroll-jack.

## PRINT
Mono headings, proportional body. Footer: page#, doc ID, rev date (mono). Table borders 0.5pt. Margins 1in. Figures: FIG-01 IDs.

## DENSITY CHECK
50+ data points visible without scroll? Padding >8px justified? Nothing hidden that fits? Min font size? Full-width data? Status bar present? Numbers right-aligned tabular? Color = meaning? Can spacing shrink to fit more? If yes → do it.

## NEVER
rounded corners >4px, drop shadows, gradients, hamburger(desktop), skeleton animations, emoji, stock photos, micro-interactions, trending typefaces, large-padding cards, purple-gradient heroes, padding >16px in panels, tabs hiding fittable content, "show more" links, single-col data layouts, font >14px for data, separate detail pages, empty state illustrations, tooltips for displayable data.

## REF
diskprices.com · AD datasheets · Bloomberg Terminal · neil.computer · Thorlabs · Bell Labs memos · NASA MCC · Garmin G3000 · Collins Pro Line Fusion · ATC radar
