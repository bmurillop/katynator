/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
    './node_modules/@tremor/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Brand palette — MY Finanzas
        'brown-900': '#5C3318',
        'brown-600': '#8C5E38',
        'amber-500': '#C99828',
        'cream':     '#F0EDD5',
        'green-800': '#3D5C1A',
        'green-600': '#6B8840',
        // Near-black for text on light backgrounds
        'ink':       '#2C1A0A',
        // Tremor primary → amber, light backgrounds
        tremor: {
          brand: {
            faint:    '#fdf9ee',
            muted:    '#fef3c7',
            subtle:   '#fcd34d',
            DEFAULT:  '#C99828',
            emphasis: '#b45309',
            inverted: '#2C1A0A',
          },
          background: {
            muted:    '#F5EFE0',
            subtle:   '#FAF7EF',
            DEFAULT:  '#FFFFFF',
            emphasis: '#5C3318',
          },
          border:  { DEFAULT: '#8C5E38' },
          ring:    { DEFAULT: '#C99828' },
          content: {
            subtle:   '#8C5E38',
            DEFAULT:  '#2C1A0A',
            emphasis: '#2C1A0A',
            strong:   '#5C3318',
            inverted: '#F0EDD5',
          },
        },
      },
      boxShadow: {
        'tremor-input':    '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'tremor-card':     '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'tremor-dropdown': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
      },
      borderRadius: {
        'tremor-small':   '0.375rem',
        'tremor-default': '0.5rem',
        'tremor-full':    '9999px',
      },
      fontSize: {
        'tremor-label':   ['0.75rem'],
        'tremor-default': ['0.875rem', { lineHeight: '1.25rem' }],
        'tremor-title':   ['1.125rem', { lineHeight: '1.75rem' }],
        'tremor-metric':  ['1.875rem', { lineHeight: '2.25rem' }],
      },
    },
  },
  safelist: [
    {
      pattern: /^(bg|text|border|ring|stroke|fill)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ['hover', 'ui-selected'],
    },
  ],
  plugins: [],
}
