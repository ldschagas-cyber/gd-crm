import { useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { useSoftphone } from '../context/SoftphoneContext.jsx'
import {
  avatarUrl, changeMyPassword, connectIntegration, disconnectIntegration, getIntegration,
  removeAvatar, updateMe, uploadAvatar,
} from '../api/me'
import { initials } from '../utils/avatar'
import '../styles/dataTable.css'
import './PreferenciasPage.css'

const TABS = [
  { key: 'perfil', label: 'Perfil' },
  { key: 'email', label: 'E-mail' },
  { key: 'chamadas', label: 'Chamadas' },
  { key: 'calendario', label: 'Calendário' },
  { key: 'whatsapp', label: 'WhatsApp' },
]

export default function PreferenciasPage() {
  const [searchParams] = useSearchParams()
  const tabFromUrl = searchParams.get('tab')
  const [tab, setTab] = useState(TABS.some((t) => t.key === tabFromUrl) ? tabFromUrl : 'perfil')

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Preferências pessoais</h1>
          <p>Configurações da sua própria conta — diferente de Configurações do tenant</p>
        </div>
      </header>

      <div className="content">
        <div className="pref-tabs">
          {TABS.map((t) => (
            <button key={t.key} className={`pref-tab${tab === t.key ? ' active' : ''}`} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'perfil' && <PerfilTab />}
        {tab === 'email' && <IntegrationTab tipo="email" title="E-mail" description="Envie e receba e-mails direto do CRM, sincronizado com sua conta Microsoft 365." />}
        {tab === 'chamadas' && <ChamadasTab />}
        {tab === 'calendario' && <IntegrationTab tipo="calendario" title="Calendário" description="Sincronize reuniões e compromissos com o seu calendário do Microsoft 365." />}
        {tab === 'whatsapp' && <WhatsappTab />}
      </div>
    </>
  )
}

function PerfilTab() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    nome: user?.nome ?? '', telefone: user?.telefone ?? '', cargo: user?.cargo ?? '',
  })
  const [pwd, setPwd] = useState({ senha_atual: '', senha_nova: '' })
  const [pwdMsg, setPwdMsg] = useState(null)
  const [avatarError, setAvatarError] = useState(null)
  const fileInputRef = useRef(null)

  const profileMutation = useMutation({
    mutationFn: updateMe,
    onSuccess: () => refreshUser(),
  })
  const avatarMutation = useMutation({
    mutationFn: uploadAvatar,
    onSuccess: () => { setAvatarError(null); refreshUser() },
    onError: (err) => setAvatarError(err.response?.data?.error?.message ?? 'Não foi possível enviar a foto.'),
  })
  const removeAvatarMutation = useMutation({
    mutationFn: removeAvatar,
    onSuccess: () => refreshUser(),
  })
  const passwordMutation = useMutation({
    mutationFn: changeMyPassword,
    onSuccess: () => { setPwdMsg({ type: 'ok', text: 'Senha alterada com sucesso.' }); setPwd({ senha_atual: '', senha_nova: '' }) },
    onError: (err) => setPwdMsg({ type: 'error', text: err.response?.data?.error?.message ?? 'Não foi possível trocar a senha.' }),
  })

  function handleProfileSubmit(e) {
    e.preventDefault()
    profileMutation.mutate({
      nome: form.nome.trim() || undefined,
      telefone: form.telefone.trim() || null,
      cargo: form.cargo.trim() || null,
    })
  }

  function handlePasswordSubmit(e) {
    e.preventDefault()
    setPwdMsg(null)
    passwordMutation.mutate(pwd)
  }

  function handleAvatarChange(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) avatarMutation.mutate(file)
  }

  return (
    <>
      <div className="card section-card">
        <div className="card-head"><h2>Foto</h2><p>Aparece no menu do avatar e para o resto da equipe</p></div>
        <div className="section-body">
          <div className="avatar-row">
            {avatarUrl(user) ? (
              <img className="avatar-lg" src={avatarUrl(user)} alt="" />
            ) : (
              <div className="avatar-lg">{initials(user?.nome)}</div>
            )}
            <div className="avatar-row-actions">
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={handleAvatarChange} />
              <button type="button" className="btn-ghost sm" disabled={avatarMutation.isPending} onClick={() => fileInputRef.current?.click()}>
                {avatarMutation.isPending ? 'Enviando…' : 'Alterar foto'}
              </button>
              {user?.avatar_url && (
                <button type="button" className="btn-ghost sm" disabled={removeAvatarMutation.isPending} onClick={() => removeAvatarMutation.mutate()}>
                  Remover foto
                </button>
              )}
            </div>
          </div>
          {avatarError && <p className="state-msg error">{avatarError}</p>}
        </div>
      </div>

      <form className="card section-card" onSubmit={handleProfileSubmit}>
        <div className="card-head"><h2>Dados pessoais</h2><p>Como você aparece para o resto da equipe</p></div>
        <div className="section-body">
          <div className="f-group">
            <label className="f-label">Nome</label>
            <input className="f-input" value={form.nome} onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))} />
          </div>
          <div className="f-group">
            <label className="f-label">E-mail</label>
            <input className="f-input" value={user?.email ?? ''} disabled />
          </div>
          <div className="f-row">
            <div className="f-group">
              <label className="f-label">Telefone <span className="opt">opcional</span></label>
              <input className="f-input" value={form.telefone} onChange={(e) => setForm((f) => ({ ...f, telefone: e.target.value }))} />
            </div>
            <div className="f-group">
              <label className="f-label">Cargo <span className="opt">opcional</span></label>
              <input className="f-input" value={form.cargo} onChange={(e) => setForm((f) => ({ ...f, cargo: e.target.value }))} />
            </div>
          </div>
          {profileMutation.isSuccess && <p className="state-msg ok">Perfil atualizado.</p>}
          {profileMutation.isError && <p className="state-msg error">Não foi possível salvar.</p>}
        </div>
        <div className="section-foot">
          <button type="submit" className="btn-primary" disabled={profileMutation.isPending}>
            {profileMutation.isPending ? 'Salvando…' : 'Salvar alterações'}
          </button>
        </div>
      </form>

      <form className="card section-card" onSubmit={handlePasswordSubmit}>
        <div className="card-head"><h2>Segurança</h2><p>Troque sua senha de acesso</p></div>
        <div className="section-body">
          <div className="f-group">
            <label className="f-label">Senha atual <span className="req">*</span></label>
            <input className="f-input" type="password" required value={pwd.senha_atual} onChange={(e) => setPwd((p) => ({ ...p, senha_atual: e.target.value }))} />
          </div>
          <div className="f-group">
            <label className="f-label">Nova senha <span className="req">*</span></label>
            <input className="f-input" type="password" required minLength={8} value={pwd.senha_nova} onChange={(e) => setPwd((p) => ({ ...p, senha_nova: e.target.value }))} placeholder="Mínimo 8 caracteres" />
          </div>
          {pwdMsg && <p className={`state-msg ${pwdMsg.type === 'error' ? 'error' : 'ok'}`}>{pwdMsg.text}</p>}
        </div>
        <div className="section-foot">
          <button type="submit" className="btn-primary" disabled={passwordMutation.isPending}>
            {passwordMutation.isPending ? 'Salvando…' : 'Trocar senha'}
          </button>
        </div>
      </form>
    </>
  )
}

function IntegrationTab({ tipo, title, description }) {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['integration', tipo], queryFn: () => getIntegration(tipo) })

  const connectMutation = useMutation({
    mutationFn: () => connectIntegration(tipo),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integration', tipo] }),
  })
  const disconnectMutation = useMutation({
    mutationFn: () => disconnectIntegration(tipo),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integration', tipo] }),
  })

  const data = query.data

  return (
    <div className="card section-card">
      <div className="card-head"><h2>{title}</h2><p>{description}</p></div>
      <div className="section-body">
        {query.isLoading && <p className="state-msg">Carregando…</p>}
        {data && (
          <div className="integration-row">
            <div className="integration-status">
              <span className={`status-dot${data.conectado ? ' on' : ''}`} />
              {data.conectado ? 'Conectado à Microsoft 365' : 'Não conectado'}
            </div>
            {data.conectado ? (
              <button className="btn-ghost" disabled={disconnectMutation.isPending} onClick={() => disconnectMutation.mutate()}>
                {disconnectMutation.isPending ? 'Desconectando…' : 'Desconectar'}
              </button>
            ) : (
              <button className="btn-primary" disabled={connectMutation.isPending} onClick={() => connectMutation.mutate()}>
                Conectar com Microsoft 365
              </button>
            )}
          </div>
        )}
        {connectMutation.isError && (
          <p className="state-msg error">
            {connectMutation.error.response?.data?.error?.message ?? 'Não foi possível conectar.'}
          </p>
        )}
      </div>
    </div>
  )
}

function ChamadasTab() {
  const { conectado, error } = useSoftphone()
  return (
    <div className="card section-card">
      <div className="card-head"><h2>Chamadas</h2><p>Ligações direto do CRM via Twilio Voice — saída e entrada</p></div>
      <div className="section-body">
        <div className="integration-row">
          <div className="integration-status">
            <span className={`status-dot${conectado ? ' on' : ''}`} />
            {conectado ? 'Chamadas conectadas (Twilio Voice)' : 'Chamadas ainda não configuradas'}
          </div>
        </div>
        {conectado ? (
          <>
            <p className="pref-info">
              Ligar direto de um contato, empresa ou negócio já usa o discador embutido (botão "Ligar" no lugar
              do link <code>tel:</code>). Chamadas recebidas no número da empresa tocam aqui no navegador — fica
              um aviso no canto da tela pra atender ou recusar.
            </p>
            <p className="pref-info">
              Toda ligação (feita ou recebida) fica registrada automaticamente na timeline da empresa, com
              duração e horário.
            </p>
          </>
        ) : (
          <p className="pref-info">
            Peça ao administrador do CRM para configurar as credenciais do Twilio (Account SID, API Key,
            TwiML App e o número de telefone) no servidor. Enquanto isso, os botões de telefone continuam
            usando o link <code>tel:</code> do seu dispositivo, como hoje.
          </p>
        )}
        {error && <p className="state-msg error">{error}</p>}
      </div>
    </div>
  )
}

function WhatsappTab() {
  return (
    <div className="card section-card">
      <div className="card-head"><h2>WhatsApp</h2><p>Avaliação da integração com WhatsApp Business API</p></div>
      <div className="section-body">
        <p className="pref-info">
          Hoje o CRM usa apenas o link <code>wa.me</code> (abre o WhatsApp Web/app manualmente) em Contatos e no
          detalhe da Empresa — sem envio, recebimento ou registro automático de mensagens.
        </p>
        <p className="pref-info">
          <strong>O gargalo real não é técnico, é o cadastro no Meta.</strong> Pra ter um número de WhatsApp
          próprio via API (Twilio ou qualquer provedor), a GD Conecta precisa de uma conta Meta Business Manager
          verificada (documentos: CNPJ/contrato social, comprovante), 2FA ativo, e um número dedicado que não
          esteja em uso num WhatsApp pessoal/comum — a verificação do Meta pode levar <strong>semanas</strong>,
          então esse é o passo com maior lead time, não a integração em si.
        </p>
        <p className="pref-info">
          <strong>Custo:</strong> desde jul/2025 o Meta cobra por mensagem (não mais por "conversa"). No Brasil,
          hoje: mensagem de marketing ≈ R$0,39, utilitária ≈ R$0,08, autenticação ≈ R$0,09 — mais a taxa própria
          do Twilio de ≈US$0,005 por mensagem em cima disso. Toda mensagem iniciada pela empresa (não em resposta
          a um cliente) precisa de um <em>template</em> pré-aprovado pelo Meta, categorizado como
          marketing/utilitário/autenticação.
        </p>
        <p className="pref-info">
          <strong>Recomendação:</strong> se decidir seguir, o primeiro passo real é abrir a verificação da Meta
          Business Manager agora (é o item que não dá pra acelerar depois) — a implementação técnica em si
          (webhook de entrada, envio via API, registro na timeline) é reaproveitável do mesmo padrão já usado
          para E-mail. Ainda não iniciar a implementação até essa decisão.
        </p>
      </div>
    </div>
  )
}
