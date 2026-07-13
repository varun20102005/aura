import { createStitches } from '@stitches/react';

export const {
  styled,
  css,
  globalCss,
  keyframes,
  getCssText,
  theme,
  createTheme,
  config,
} = createStitches({
  theme: {
    colors: {
      bg: '#0b0f19',
      surface: 'rgba(16, 19, 26, 0.7)', // '#10131a' with opacity
      surfaceHover: 'rgba(16, 19, 26, 0.9)',
      border: 'rgba(255, 255, 255, 0.1)', // white/10
      borderFocus: 'rgba(173, 198, 255, 0.5)',
      textPrimary: '#e3e2e7', // on-surface
      textSecondary: '#c2c6d6', // on-surface-variant
      textMuted: '#8e909a', // outline
      accent: '#adc6ff', // primary
      accentHover: '#d8e2ff', // primary bright
      accentGlow: 'rgba(173, 198, 255, 0.2)', // glow
      danger: '#ffb4ab',
      warning: '#ffb786', // tertiary-gold
      success: '#4ade80',
      white: '#ffffff',
      // Chart colors
      chartPrimary: '#adc6ff',
      chartSuccess: '#4ade80',
    },
    space: {
      1: '4px',
      2: '8px',
      3: '16px',
      4: '24px',
      5: '32px',
      6: '40px',
    },
    fonts: {
      base: "'Inter', system-ui, -apple-system, sans-serif",
    },
    fontSizes: {
      displayLg: '48px',
      headlineLg: '32px',
      headlineMd: '24px',
      bodyLg: '18px',
      bodyMd: '16px',
      bodySm: '14px',
      labelCaps: '12px',
    },
    radii: {
      sm: '0.125rem',
      DEFAULT: '0.25rem',
      md: '0.375rem',
      lg: '0.5rem',
      xl: '0.75rem',
      round: '9999px',
    },
    shadows: {
      base: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
      cardHover: '0 20px 40px rgba(0,0,0,0.4), 0 0 20px rgba(59, 130, 246, 0.1)',
      glow: '0 4px 15px rgba(173, 198, 255, 0.3)',
    },
    transitions: {
      base: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    }
  },
  utils: {
    paddingX: (value) => ({ paddingLeft: value, paddingRight: value }),
    paddingY: (value) => ({ paddingTop: value, paddingBottom: value }),
    marginX: (value) => ({ marginLeft: value, marginRight: value }),
    marginY: (value) => ({ marginTop: value, marginBottom: value }),
  }
});
