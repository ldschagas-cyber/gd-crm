// Paleta sequencial usada pra distinguir etapas abertas visualmente (dataTable.css / tokens.css).
const SEQ_PALETTE = ['var(--seq-1)', 'var(--seq-2)', 'var(--seq-3)', 'var(--seq-4)', 'var(--seq-5)', 'var(--seq-6)']

// `openIndex` é a posição da etapa entre as etapas ABERTAS (não terminais) do pipeline,
// pra manter a mesma cor em qualquer tela que mostrar essa etapa.
export function stageTint(openIndex) {
  return SEQ_PALETTE[openIndex % SEQ_PALETTE.length]
}

export function stageColorMode(pipeline) {
  return pipeline?.cor_exibicao ?? 'sem_cor'
}

// Mapa stageId -> cor, na mesma ordem usada na tela de Pipeline (só etapas abertas contam pra cor).
export function buildStageTintMap(stages) {
  const open = [...(stages ?? [])]
    .filter((s) => s.tipo === 'aberta')
    .sort((a, b) => a.ordem - b.ordem)
  return Object.fromEntries(open.map((s, i) => [s.id, stageTint(i)]))
}
