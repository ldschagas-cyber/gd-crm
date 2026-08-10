import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listSnippets } from '../api/snippets'
import { insertSnippetAtCursor } from '../utils/snippets'
import './SnippetInsertButton.css'

/** Botão "+ Inserir snippet" pra qualquer campo de texto controlado — usado no
 * campo de Roteiro das tarefas (TaskModal e painel de ligação da fila de
 * execução). Complementa a expansão por `#atalho` de `utils/snippets.js`: aqui
 * o usuário escolhe visualmente em vez de decorar o atalho. */
export default function SnippetInsertButton({ targetRef, value, onChange, vars }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const snippetsQuery = useQuery({ queryKey: ['snippets', 'for-insert'], queryFn: () => listSnippets({ size: 100 }) })
  const snippets = snippetsQuery.data?.items ?? []

  useEffect(() => {
    if (!open) return
    function onDocClick(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  function pick(snippet) {
    insertSnippetAtCursor(targetRef.current, value, onChange, snippet, vars)
    setOpen(false)
  }

  return (
    <span className="snippet-insert" ref={wrapRef}>
      <button type="button" className="snippet-insert-btn" onClick={() => setOpen((o) => !o)}>
        + Inserir snippet
      </button>
      {open && (
        <div className="snippet-insert-menu">
          {snippets.length === 0 && (
            <div className="snippet-insert-empty">
              Nenhum snippet cadastrado ainda — crie um em Snippets.
            </div>
          )}
          {snippets.map((s) => (
            <button type="button" key={s.id} className="snippet-insert-opt" onClick={() => pick(s)}>
              <b>{s.nome}</b>
              <span>#{s.atalho}</span>
            </button>
          ))}
        </div>
      )}
    </span>
  )
}
