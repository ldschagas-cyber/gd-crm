// Ícone + rótulo por tipo de atividade (Tarefa/Sequência/Workflow) — fonte única
// para não duplicar os 7 tipos em cada tela (Tarefas, Sequências, Workflows).
export const TIPO_LABEL = {
  ligacao: 'Ligação',
  email: 'E-mail',
  email_manual: 'E-mail (manual)',
  whatsapp: 'WhatsApp',
  reuniao: 'Reunião',
  linkedin_conexao: 'LinkedIn (conexão)',
  linkedin_mensagem: 'LinkedIn (mensagem)',
  followup: 'Follow-up',
}

function Phone() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path d="M5.5 3.5c.6 0 1.1.4 1.3 1l.7 1.9c.2.5 0 1-.3 1.3l-1 .9c.6 1.6 1.9 2.9 3.5 3.5l.9-1c.3-.3.9-.5 1.3-.3l1.9.7c.6.2 1 .7 1 1.3v1.7c0 .8-.7 1.4-1.5 1.3-6-.6-9.6-4.2-10.2-10.2-.1-.8.5-1.5 1.3-1.5z" />
    </svg>
  )
}
function Envelope() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="4" width="15" height="12" rx="1.8" />
      <path d="M3 5l7 5.5L17 5" />
    </svg>
  )
}
function EnvelopeManual() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1.8" y="3.5" width="12" height="9.6" rx="1.5" />
      <path d="M2.4 4.4l5.4 4.3L13.2 4.4" />
      <path d="M12.6 17.1l.8-3 5-5a1.1 1.1 0 011.5 1.5l-5 5-3 .8z" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
function Whatsapp() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2a10 10 0 00-8.6 15.1L2 22l5.1-1.3A10 10 0 1012 2zm0 18.2a8.1 8.1 0 01-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.1 8.1 0 1112 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1s-.6.8-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 01-2-1.2 7.4 7.4 0 01-1.4-1.7c-.1-.2 0-.4.1-.5l.4-.4c.1-.1.2-.3.2-.4a.5.5 0 000-.5c-.1-.1-.6-1.5-.9-2-.2-.5-.5-.4-.6-.4h-.5a1 1 0 00-.7.3 3 3 0 00-.9 2.2c0 1.3.9 2.6 1.1 2.8.1.2 2 3 4.8 4.2.7.3 1.2.5 1.6.6a3.9 3.9 0 001.8.1c.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.2-.2-.4-.3z" />
    </svg>
  )
}
function Calendar() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="4.2" width="14" height="12.3" rx="1.8" />
      <path d="M3 8h14M7 2.5v3M13 2.5v3" strokeLinecap="round" />
    </svg>
  )
}
function LinkedinConnect() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="7.8" cy="6.8" r="3" />
      <path d="M2.5 17c0-3 2.3-5 5.3-5s5.3 2 5.3 5" strokeLinecap="round" />
      <path d="M14.7 6.3h3.3M16.35 4.65v3.3" strokeLinecap="round" />
    </svg>
  )
}
function LinkedinLogo() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M6.94 5a1.94 1.94 0 11-3.88 0 1.94 1.94 0 013.88 0zM3.34 8.75h3.2V21h-3.2zM9.9 8.75h3.07v1.68h.04c.43-.8 1.47-1.65 3.02-1.65 3.23 0 3.83 2.13 3.83 4.9V21h-3.2v-5.62c0-1.34-.02-3.06-1.87-3.06-1.87 0-2.15 1.46-2.15 2.97V21H9.9z" />
    </svg>
  )
}
function Checklist() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="14" height="14" rx="2.2" />
      <path d="M6.6 10.2l2 2 4.6-4.9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const ICONS = {
  ligacao: Phone,
  email: Envelope,
  email_manual: EnvelopeManual,
  whatsapp: Whatsapp,
  reuniao: Calendar,
  linkedin_conexao: LinkedinConnect,
  linkedin_mensagem: LinkedinLogo,
  followup: Checklist,
}

export function TaskTypeIcon({ tipo }) {
  const Cmp = ICONS[tipo]
  if (!Cmp) return null
  return (
    <span className="tipo-icon">
      <Cmp />
    </span>
  )
}

export function TaskTypeChip({ tipo }) {
  return (
    <span className="tipo-chip">
      <TaskTypeIcon tipo={tipo} />
      {TIPO_LABEL[tipo] ?? tipo}
    </span>
  )
}
