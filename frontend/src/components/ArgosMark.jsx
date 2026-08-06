// Símbolo da marca Argos — íris: anel com pupila concêntrica, geometria pura (sem letras).
// Construção (Manual da Marca Argos V1): sobre diâmetro externo D, espessura do anel = 0.115D,
// diâmetro da pupila = 0.32D, sempre concêntrica. Abaixo de 20px a pupila fecha visualmente —
// usar a variante de anel grosso sem pupila (ver prop `size`).
//
// Cores por contexto (não recolorir fora desta tabela — regra do manual):
//   dark  (fundo #232748, painel/sidebar) -> anel dourado, pupila dourada
//   light (fundo claro, cards)            -> anel azul-noite, pupila dourada
//   monoPositive (impressão 1 cor, positivo) -> tudo #1B1D33
//   monoNegative (impressão 1 cor, negativo) -> tudo #FFFFFF
const VARIANTS = {
  dark: { ring: '#D9B654', pupil: '#D9B654' },
  light: { ring: '#2B2F5E', pupil: '#D9B654' },
  monoPositive: { ring: '#1B1D33', pupil: '#1B1D33' },
  monoNegative: { ring: '#FFFFFF', pupil: '#FFFFFF' },
}

export default function ArgosMark({ size = 32, variant = 'dark', className }) {
  const { ring, pupil } = VARIANTS[variant] ?? VARIANTS.dark
  const showPupil = size >= 20
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <circle
        cx="50"
        cy="50"
        r="44.25"
        fill="none"
        stroke={ring}
        strokeWidth={showPupil ? 11.5 : 15}
      />
      {showPupil && <circle cx="50" cy="50" r="16" fill={pupil} />}
    </svg>
  )
}
