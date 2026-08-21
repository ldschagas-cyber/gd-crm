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
    label: 'Gestão',
    items: [
      { to: '/', label: 'Dashboard', end: true, icon: IconDashboard },
      { to: '/metas-funil', label: 'Metas do Funil', icon: IconTarget },
      { to: '/metas-vendas', label: 'Metas de Vendas', icon: IconSalesGoal },
      { to: '/metas-ligacoes', label: 'Metas de Ligações', icon: IconPhone },
      { to: '/previsao-comercial', label: 'Previsão Comercial', icon: IconForecast },
    ],
  },
  {
    label: 'Inteligência Comercial',
    items: [
      { to: '/buscar-empresas', label: 'Buscar Empresas', icon: IconSearch },
      { to: '/pesquisa-leads', label: 'Pesquisa de Leads', icon: IconRadar },
      { to: '/central-leads', label: 'Central de Leads', icon: IconFunnel },
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
      { to: '/modelos-mensagem', label: 'Modelos de mensagem', icon: IconMessageTemplate },
      { to: '/snippets', label: 'Respostas rápidas', icon: IconSnippet },
      { to: '/formularios', label: 'Formulários', icon: IconForm },
    ],
  },
  {
    label: 'Customer Success',
    items: [
      { to: '/clientes', label: 'Clientes', icon: IconCustomerSuccess },
    ],
  },
  {
    label: 'Receita',
    items: [
      { to: '/receita-recorrente', label: 'Receita Recorrente', icon: IconRevenue },
    ],
  },
  {
    label: 'Financeiro',
    items: [
      { to: '/financeiro', label: 'Visão Geral', end: true, icon: IconFinanceiro },
      { to: '/financeiro/produtos', label: 'Produtos', icon: IconProduto },
      { to: '/financeiro/propostas', label: 'Propostas', icon: IconProposta },
      { to: '/financeiro/faturamento', label: 'Faturamento', icon: IconFaturamento },
    ],
  },
]

const SIDEBAR_COLLAPSED_KEY = 'argos.sidebarCollapsed'
const SIDEBAR_GROUPS_COLLAPSED_KEY = 'argos.sidebarCollapsedGroups'

function readCollapsedGroups() {
  try {
    const raw = JSON.parse(localStorage.getItem(SIDEBAR_GROUPS_COLLAPSED_KEY) ?? '[]')
    return new Set(Array.isArray(raw) ? raw : [])
  } catch {
    return new Set()
  }
}

const NAV_CONTA = [
  { to: '/preferencias', label: 'Preferências' },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')
  const [collapsedGroups, setCollapsedGroups] = useState(readCollapsedGroups)

  function toggleCollapsed() {
    setCollapsed((v) => {
      const next = !v
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0')
      return next
    })
  }

  function toggleGroup(label) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      localStorage.setItem(SIDEBAR_GROUPS_COLLAPSED_KEY, JSON.stringify([...next]))
      return next
    })
  }

  const tenantQuery = useQuery({ queryKey: ['tenant'], queryFn: getTenant, staleTime: Infinity })
  const tenantNome = tenantQuery.data?.nome_fantasia || tenantQuery.data?.razao_social

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <SoftphoneProvider>
    <div className={`shell${collapsed ? ' sidebar-collapsed' : ''}`}>
      {sidebarOpen && <div className="sidebar-scrim" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}${collapsed ? ' collapsed' : ''}`}>
        <div className="sb-brand">
          <ArgosMark size={26} variant="dark" />
          <div>
            <strong>Argos</strong>
            <span>By GD Conecta</span>
          </div>
        </div>

        <nav className="sb-nav">
          {NAV_GROUPS.map((group, i) => {
            const groupCollapsed = Boolean(group.label) && collapsedGroups.has(group.label) && !collapsed
            return (
              <div className="sb-group" key={group.label ?? i}>
                {group.label && (
                  <button
                    type="button"
                    className="sb-label"
                    onClick={() => toggleGroup(group.label)}
                    aria-expanded={!groupCollapsed}
                  >
                    <span className="sb-label-text">{group.label}</span>
                    <IconChevron className={`sb-label-chevron${groupCollapsed ? ' collapsed' : ''}`} />
                  </button>
                )}
                <div className={`sb-group-items${groupCollapsed ? ' collapsed' : ''}`}>
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) => `sb-item${isActive ? ' active' : ''}`}
                      onClick={() => setSidebarOpen(false)}
                      title={collapsed ? item.label : undefined}
                      tabIndex={groupCollapsed ? -1 : undefined}
                    >
                      <item.icon />
                      <span className="sb-item-label">{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            )
          })}
        </nav>

        <button
          type="button"
          className="sb-collapse-toggle"
          onClick={toggleCollapsed}
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          <IconCollapse collapsed={collapsed} />
          <span className="sb-item-label">Recolher menu</span>
        </button>
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

function IconChevron({ className }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M6 8l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function IconCollapse({ collapsed }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="3.5" width="15" height="13" rx="1.8" />
      <path d="M8 3.5v13" />
      {collapsed ? <path d="M11.5 7l2.3 3-2.3 3" strokeLinecap="round" strokeLinejoin="round" /> : <path d="M13.8 7l-2.3 3 2.3 3" strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
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
function IconFunnel() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 3.5h14l-5.3 6.6v5.4l-3.4 1.7v-7.1z" strokeLinejoin="round" />
    </svg>
  )
}

function IconTarget() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7" />
      <circle cx="10" cy="10" r="3.6" />
      <circle cx="10" cy="10" r=".9" fill="currentColor" stroke="none" />
    </svg>
  )
}
function IconForecast() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 15l4-5 3.5 3L17 5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12.5 5H17v4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconRevenue() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 15.5h14M3 15.5V4.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 12.5v-3M10 12.5V6.5M14 12.5v-5.5" strokeLinecap="round" />
    </svg>
  )
}

function IconFinanceiro() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6v8M8 8h3a1.5 1.5 0 0 1 0 3H8.5M8 11h3.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconProduto() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M10 2.8 16.5 6v8L10 17.2 3.5 14V6L10 2.8Z" strokeLinejoin="round" />
      <path d="M3.7 6.2 10 9.5l6.3-3.3M10 9.5v7.6" strokeLinejoin="round" />
    </svg>
  )
}

function IconProposta() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M5 2.8h7l3 3v11.4H5V2.8Z" strokeLinejoin="round" />
      <path d="M12 2.8v3h3M7.5 10h5M7.5 13h5" strokeLinecap="round" />
    </svg>
  )
}

function IconFaturamento() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M5 2.8h10v14.4l-2-1.3-1.7 1.3L10 15.9 8.3 17.2 6.6 15.9 5 17.2V2.8Z" strokeLinejoin="round" />
      <path d="M7.5 7h5M7.5 10h5" strokeLinecap="round" />
    </svg>
  )
}
function IconSalesGoal() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6.4v7.2M8.2 12.3c0 .9.8 1.5 1.8 1.5s1.8-.5 1.8-1.4c0-2-3.4-1.2-3.4-3.1 0-.9.8-1.4 1.8-1.4s1.8.6 1.8 1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function IconPhone() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M6.2 3.5c.4 0 .8.3.9.7l.8 2.4c.1.4 0 .8-.3 1L6.5 8.6c.8 1.7 2.2 3.1 3.9 3.9l1-1.1c.3-.3.7-.4 1-.3l2.4.8c.4.1.7.5.7.9v2.4c0 .6-.5 1.1-1.1 1C8.9 16.1 3.9 11.1 3.3 5.7c-.1-.6.4-1.1 1-1.1z" strokeLinejoin="round" />
    </svg>
  )
}
function IconCustomerSuccess() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7.3" />
      <path d="M6.7 10.3l2.1 2.2 4.5-4.7" strokeLinecap="round" strokeLinejoin="round" />
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
function IconMessageTemplate() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 17l1.1-3.4a6.9 6.9 0 113 2.7z" />
      <path d="M7.3 8.3c.2 2.4 2 4.2 4.4 4.4" />
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
