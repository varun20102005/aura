---
name: Aegis Command
colors:
  surface: '#10131a'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e11'
  surface-container-low: '#1a1b1f'
  surface-container: '#1e1f23'
  surface-container-high: '#292a2d'
  surface-container-highest: '#343538'
  on-surface: '#e3e2e7'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3034'
  outline: '#8e909a'
  outline-variant: '#44474f'
  surface-tint: '#adc6ff'
  primary: '#d8e2ff'
  on-primary: '#122f5f'
  primary-container: '#adc6ff'
  on-primary-container: '#385283'
  inverse-primary: '#455e90'
  secondary: '#c4c6cf'
  on-secondary: '#2d3037'
  secondary-container: '#464950'
  on-secondary-container: '#b6b8c1'
  tertiary: '#ffdea4'
  on-tertiary: '#412d00'
  tertiary-container: '#ebc06e'
  on-tertiary-container: '#6c4d01'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#2c4677'
  secondary-fixed: '#e0e2eb'
  secondary-fixed-dim: '#c4c6cf'
  on-secondary-fixed: '#181c22'
  on-secondary-fixed-variant: '#44474e'
  tertiary-fixed: '#ffdea5'
  tertiary-fixed-dim: '#ebc06e'
  on-tertiary-fixed: '#261900'
  on-tertiary-fixed-variant: '#5d4200'
  background: '#0b0f19'
  on-background: '#e3e2e7'
  surface-variant: '#343538'
  tertiary-gold: '#ffb786'
  success-green: '#4ade80'
  error-red: '#ffb4ab'
  glass-fill: rgba(30, 41, 59, 0.7)
  accent-glow: rgba(173, 198, 255, 0.2)
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  value-bold:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
  gutter: 24px
  container-padding-desktop: 32px
  container-padding-mobile: 16px
---

## Brand & Style

Aegis Command is an elite enterprise monitoring platform designed for systems architects and security professionals. The visual language evokes a high-stakes "Mission Control" or "Tech Noir" aesthetic. It balances institutional reliability with cutting-edge technical sophistication.

The design style is **Glassmorphism mixed with High-Contrast Accents**. It utilizes deep obsidian surfaces, frosted translucent layers, and vibrant electric blue "glow" accents to simulate a futuristic heads-up display (HUD). The brand is authoritative, precise, and highly functional, prioritizing data density without sacrificing visual elegance.

## Colors

The color palette is built on a "Deep Space" foundation to minimize eye strain during long-term monitoring.

- **Primary (#adc6ff):** A desaturated electric blue used for interactive elements, active states, and high-priority data points.
- **Background (#0b0f19):** A near-black navy that serves as the base canvas.
- **Semantic Accents:** 
  - **Tertiary Gold (#ffb786):** Reserved for warnings, pending states, and notifications.
  - **Success Green (#4ade80):** Indicates optimal system health and completed actions.
  - **Error Red (#ffb4ab):** Critical failures and destructive actions (e.g., Logout).
- **Glass Surfaces:** Semi-transparent fills combined with `backdrop-filter: blur(12px)` and subtle white/10 borders create the signature depth.

## Typography

The system uses **Inter** exclusively to maintain a utilitarian, technical feel. 

- **Data Presentation:** Large displays (`display-lg`) are used for primary metrics like revenue or node counts.
- **Hierarchy:** Use `label-caps` for all metadata, sidebar navigation items, and section subtitles to create a "terminal-inspired" look.
- **Density:** Body text is kept small and precise to allow for high information density in tables and logs.
- **Interactions:** Use `value-bold` for button labels and key identifiers (e.g., Node IDs) to ensure they stand out against UI chrome.

## Layout & Spacing

The layout follows a **Fixed Sidebar + Fluid Content** model. 

- **Sidebar:** A fixed 256px (64 units) left-aligned navigation bar with a distinct background blur.
- **Grid:** Use a 12-column grid for the main content area with a consistent 24px gutter. 
- **Rhythm:** Vertical spacing is strictly governed by 8px increments. Cards use 24px internal padding (p-6) to breathe against the dark background.
- **Responsive:** On mobile, the sidebar transitions to a bottom navigation bar or a hidden drawer, and container padding reduces from 32px to 16px. Content cards reflow from a 4-column layout to a single-column stack.

## Elevation & Depth

Depth is not communicated through shadows alone, but through **Tonal Layering and Translucency**.

- **Level 0 (Background):** Base layer (#0b0f19).
- **Level 1 (Sidebars/Headers):** `surface/70` with `backdrop-blur-xl`. These are visually "higher" than the background but "lower" than cards.
- **Level 2 (Cards):** The `glass-card` component uses a slightly lighter fill with a 1px `white/10` border. 
- **Level 3 (Hover/Active):** Elevated cards use a specific dual shadow: a large dark diffuse shadow (`0 20px 40px rgba(0,0,0,0.4)`) and a subtle blue outer glow (`0 0 20px rgba(59, 130, 246, 0.1)`).
- **Accents:** Every card features a `glow-accent` (a top-aligned 1px gradient) to simulate light catching the edge of a glass pane.

## Shapes

The shape language is "Soft-Technical." 

- **Standard Elements:** Buttons and small cards use a 0.5rem (rounded-lg) radius.
- **Large Containers:** Main dashboard cards and the sidebar use a 0.75rem (rounded-xl) radius.
- **Search & Pills:** Inputs and status badges use "Full" rounding (9999px) to provide a soft contrast to the otherwise rigid grid.
- **Interactive States:** Buttons should subtly scale down (active:scale-95) when pressed to provide tactile physical feedback.

## Components

- **Glass Cards:** The core container. Must include a 1px border, backdrop-blur, and a top `glow-accent`. Hover states include a vertical translate (-4px) and blue-tinted shadow.
- **Action Buttons:**
    - **Primary:** Full `primary` color fill with `on-primary` text. Always features a soft blue drop shadow.
    - **Ghost:** `white/10` border with transparent background. Becomes `white/5` on hover.
- **Status Badges:** Small, pill-shaped indicators using 10% opacity fills of semantic colors (Green, Red, Blue, Gold) with matching high-contrast text. Include a 4px circular dot for "live" status.
- **Navigation:** Sidebar links use a 4px left-aligned primary-colored border-strike to indicate the active page, accompanied by a 20% opacity primary fill.
- **Inputs:** Search bars should be pill-shaped with a 20% black fill, appearing "sunken" into the glass header.
- **Progress Bars:** Thin 4px tracks with solid fills. High-priority bars should have a subtle outer glow matching their fill color.