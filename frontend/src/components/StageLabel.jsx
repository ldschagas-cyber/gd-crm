// Mostra o nome de uma etapa de pipeline de acordo com `cor_exibicao` do pipeline
// (sem_cor / ponto / selo) — usado em Pipeline (preview) e Negócios (kanban/lista).
export default function StageLabel({ nome, mode = 'sem_cor', tint }) {
  if (mode === 'selo' && tint) {
    return <span className="stage-name-selo" style={{ background: tint }}>{nome}</span>
  }
  if (mode === 'ponto' && tint) {
    return (
      <span className="stage-name-preview">
        <span className="stage-dot" style={{ background: tint }} /> {nome}
      </span>
    )
  }
  return <span>{nome}</span>
}
