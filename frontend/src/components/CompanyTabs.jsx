import { NavLink } from 'react-router-dom'
import './CompanyTabs.css'

export default function CompanyTabs({ companyId }) {
  return (
    <nav className="co-tabs">
      <NavLink to={`/empresas/${companyId}`} end className={({ isActive }) => `co-tab${isActive ? ' active' : ''}`}>
        Visão geral
      </NavLink>
      <NavLink to={`/empresas/${companyId}/dossie`} className={({ isActive }) => `co-tab${isActive ? ' active' : ''}`}>
        Dossiê Comercial
      </NavLink>
    </nav>
  )
}
