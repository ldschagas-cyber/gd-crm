import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { SoftphoneProvider } from '../context/SoftphoneContext.jsx'
import { getTenant } from '../api/tenant'
import { avatarUrl } from '../api/me'
import { initials } from '../utils/avatar'
import Softphone from '../components/Softphone.jsx'
import ArgosMark from '../components/ArgosMark.jsx'
import './AppShell.css'

const NAV_GROUPS = [
  {
    label: null,
    items: [
      { to: '/', label: 'Dashboard', end: true, icon: IconDashboard },
    ],
  },
  {
    label: 'Inteligência Comercial',
    items: [
      { to: '/buscar-empresas', label: 'Buscar Empresas', icon: IconSearch },
      { to: '/pesquisa-leads', label: 'Pesquisa de Leads', icon: IconRadar },
    ],
  },
  {
    label: 'CRM',
    items: [
      { to: '/empresas', label: 'Empresas', icon: IconBuilding },
      { to: '/contatos', label: 'Contatos', icon: IconContact },
      { to: '/negocios', label: 'Negócios', icon: IconDeal },
      { to: '/tarefas', label: 'Tarefas', icon: IconTask },
    ],
  },
  {
    label: 'Automação',
    items: [
      { to: '/sequencias', label: 'Sequências', icon: IconSequence },
      { to: '/workflows', label: 'Workflows', icon: IconWorkflow },
      { to: '/modelos-email', label: 'Modelos de e-mail', icon: IconEmailTemplate },
      { to: '/snippets', label: 'Snippets', icon: IconSnippet },
      { to: '/formularios', label: 'Formulários', icon: IconForm },
    ],
  },
]

const NAV_CONTA = [
  { to: '/preferencias', label: 'Preferências' },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const tenantQuery = useQuery({ queryKey: ['tenant'], queryFn: getTenant, staleTime: Infinity })
  const tenantNome = tenantQuery.data?.nome_fantasia || tenantQuery.data?.razao_social

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <SoftphoneProvider>
    <div className="shell">
      {sidebarOpen && <div className="sidebar-scrim" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="sb-brand">
          <ArgosMark size={26} variant="dark" />
          <div>
            <strong>Argos</strong>
            <span>By GD Conecta</span>
          </div>
        </div>

        <nav className="sb-nav">
          {NAV_GROUPS.map((group, i) => (
            <div className="sb-group" key={group.label ?? i}>
              {group.label && <div className="sb-label">{group.label}</div>}
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `sb-item${isActive ? ' active' : ''}`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon />
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main-col">
        <header className="global-topbar">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)} aria-label="Abrir menu">
            <IconMenu />
          </button>

          <div className="tenant-pill" title="Empresa definida no login. Para trocar, saia e entre novamente.">
            <IconBuilding />
            <span>{tenantNome ?? '—'}</span>
            <IconLock />
          </div>

          <div className="global-topbar-actions">
            <NavLink to="/usuarios" className={({ isActive }) => `icon-nav-btn${isActive ? ' active' : ''}`} title="Usuários">
              <IconUsers />
            </NavLink>
            <NavLink to="/configuracoes" className={({ isActive }) => `icon-nav-btn${isActive ? ' active' : ''}`} title="Configurações">
              <IconGear />
            </NavLink>
            <div className="avatar-menu-wrap">
              <button className="topbar-avatar" onClick={() => setMenuOpen((v) => !v)}>
                {avatarUrl(user) ? <img src={avatarUrl(user)} alt="" /> : initials(user?.nome)}
              </button>
              {menuOpen && (
                <>
                  <div className="menu-scrim" onClick={() => setMenuOpen(false)} />
                  <div className="avatar-menu">
                    <div className="avatar-menu-head">
                      <strong>{user?.nome ?? '—'}</strong>
                      <span>{user?.email}</span>
                      <span className="perfil-tag">{user?.perfil}</span>
                    </div>
                    {NAV_CONTA.map((item) => (
                      <NavLink key={item.to} className="avatar-menu-item" to={item.to} onClick={() => setMenuOpen(false)}>
                        {item.label}
                      </NavLink>
                    ))}
                    <div className="avatar-menu-divider" />
                    <button className="avatar-menu-item" onClick={handleLogout}>Sair</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        <Outlet />
      </div>

      <Softphone />
    </div>
    </SoftphoneProvider>
  )
}

function IconMenu() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 5.5h14M3 10h14M3 14.5h14" strokeLinecap="round" />
    </svg>
  )
}
function IconBuilding() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 17.5V3.8a.8.8 0 01.8-.8h6.4a.8.8 0 01.8.8v13.7" />
      <path d="M13 17.5V8.3a.8.8 0 01.8-.8h3.4a.8.8 0 01.8.8v9.2" />
      <path d="M5.4 6h1.6M5.4 9h1.6M5.4 12h1.6M15 10.6h1M15 13.4h1" />
    </svg>
  )
}
function IconDashboard() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="2.5" width="6.2" height="6.2" rx="1.3" />
      <rect x="11.3" y="2.5" width="6.2" height="4.4" rx="1.3" />
      <rect x="11.3" y="9.4" width="6.2" height="8.1" rx="1.3" />
      <rect x="2.5" y="11.2" width="6.2" height="6.3" rx="1.3" />
    </svg>
  )
}
function IconRadar() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7" />
      <circle cx="10" cy="10" r="3.2" />
      <path d="M10 3v2.4M10 14.6V17M17 10h-2.4M5.4 10H3" />
    </svg>
  )
}
function IconSearch() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="8.8" cy="8.8" r="5.3" />
      <path d="M16.5 16.5l-3.8-3.8" strokeLinecap="round" />
    </svg>
  )
}

function IconContact() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="6.6" r="3.1" />
      <path d="M3.6 17c.7-3.4 3.2-5.2 6.4-5.2s5.7 1.8 6.4 5.2" />
    </svg>
  )
}
function IconDeal() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2.5 10.3l3-4.6a1 1 0 01.85-.47h7.3a1 1 0 01.85.47l3 4.6" />
      <path d="M2.5 10.3v5.2a1 1 0 001 1h13a1 1 0 001-1v-5.2" />
      <path d="M7.3 10.3a2.7 2.7 0 005.4 0" />
    </svg>
  )
}
function IconTask() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="14" height="14" rx="2.2" />
      <path d="M6.6 10.2l2 2 4.6-4.9" />
    </svg>
  )
}
function IconSequence() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 4h5.5l1.5 2h5v10H4z" />
      <path d="M8 9h4M8 12h6" />
    </svg>
  )
}
function IconWorkflow() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="5" cy="5" r="2.2" />
      <circle cx="15" cy="5" r="2.2" />
      <circle cx="10" cy="15" r="2.2" />
      <path d="M6.8 6.4L9 13.2M13.2 6.4L11 13.2" />
    </svg>
  )
}
function IconEmailTemplate() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="14" height="14" rx="1.8" />
      <path d="M6 7h8M6 10h8M6 13h5" />
    </svg>
  )
}
function IconSnippet() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M7 4L3 10l4 6M13 4l4 6-4 6" />
    </svg>
  )
}
function IconForm() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="2.5" width="14" height="15" rx="1.8" />
      <path d="M6.3 6.6h7.4M6.3 9.6h7.4M6.3 12.6h4.4" />
    </svg>
  )
}
function IconLock() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="4.5" y="9" width="11" height="7.5" rx="1.6" />
      <path d="M6.8 9V6.3a3.2 3.2 0 016.4 0V9" />
    </svg>
  )
}
function IconUsers() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="7.5" cy="6.5" r="2.8" />
      <path d="M2.6 16.4c.6-3 2.7-4.6 4.9-4.6s4.3 1.6 4.9 4.6" />
      <circle cx="14.2" cy="7.4" r="2.1" />
      <path d="M13 11.9c1.7.2 3.1 1.5 3.5 3.9" />
    </svg>
  )
}
function IconGear() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="2.6" />
      <path d="M10 2.8v2M10 15.2v2M17.2 10h-2M4.8 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3L4.9 4.9" />
    </svg>
  )
}
