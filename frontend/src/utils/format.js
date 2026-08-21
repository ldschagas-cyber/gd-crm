export function formatCurrency(v, { cents = false } = {}) {
  return (v ?? 0).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL',
    maximumFractionDigits: cents ? 2 : 0, minimumFractionDigits: cents ? 2 : 0,
  })
}

export function formatPct(v, digits = 1) {
  return `${(v ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: digits })}%`
}

export function formatDate(v) {
  if (!v) return '—'
  const d = typeof v === 'string' ? new Date(v.length <= 10 ? `${v}T00:00:00` : v) : v
  return d.toLocaleDateString('pt-BR')
}

export function competenciaLabel(competencia) {
  // "2026-08" -> "ago/2026"
  if (!competencia) return ''
  const [ano, mes] = competencia.split('-').map(Number)
  const nomes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  return `${nomes[(mes || 1) - 1]}/${ano}`
}
