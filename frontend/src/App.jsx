import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import PesquisaLeadsPage from './pages/PesquisaLeadsPage.jsx'
import CentralLeadsPage from './pages/CentralLeadsPage.jsx'
import BuscarEmpresasPage from './pages/BuscarEmpresasPage.jsx'
import EmpresasPage from './pages/EmpresasPage.jsx'
import CompanyDetailPage from './pages/CompanyDetailPage.jsx'
import CompanyDossierPage from './pages/CompanyDossierPage.jsx'
import ContatosPage from './pages/ContatosPage.jsx'
import ContactDetailPage from './pages/ContactDetailPage.jsx'
import PipelinesPage from './pages/PipelinesPage.jsx'
import NegociosPage from './pages/NegociosPage.jsx'
import DealDetailPage from './pages/DealDetailPage.jsx'
import TarefasPage from './pages/TarefasPage.jsx'
import SequenciasPage from './pages/SequenciasPage.jsx'
import WorkflowsPage from './pages/WorkflowsPage.jsx'
import ModelosEmailPage from './pages/ModelosEmailPage.jsx'
import SnippetsPage from './pages/SnippetsPage.jsx'
import FormulariosRastreioPage from './pages/FormulariosRastreioPage.jsx'
import ConfiguracoesPage from './pages/ConfiguracoesPage.jsx'
import UsuariosPage from './pages/UsuariosPage.jsx'
import PreferenciasPage from './pages/PreferenciasPage.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'
import AppShell from './layouts/AppShell.jsx'
import ProtectedRoute from './routes/ProtectedRoute.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/pesquisa-leads" element={<PesquisaLeadsPage />} />
        <Route path="/central-leads" element={<CentralLeadsPage />} />
        <Route path="/buscar-empresas" element={<BuscarEmpresasPage />} />
        <Route path="/empresas" element={<EmpresasPage />} />
        <Route path="/empresas/:id" element={<CompanyDetailPage />} />
        <Route path="/empresas/:id/dossie" element={<CompanyDossierPage />} />
        <Route path="/contatos" element={<ContatosPage />} />
        <Route path="/contatos/:id" element={<ContactDetailPage />} />
        <Route path="/negocios" element={<NegociosPage />} />
        <Route path="/negocios/:id" element={<DealDetailPage />} />
        <Route path="/pipeline" element={<PipelinesPage />} />
        <Route path="/tarefas" element={<TarefasPage />} />
        <Route path="/sequencias" element={<SequenciasPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/modelos-email" element={<ModelosEmailPage />} />
        <Route path="/snippets" element={<SnippetsPage />} />
        <Route path="/formularios" element={<FormulariosRastreioPage />} />
        <Route path="/usuarios" element={<UsuariosPage />} />
        <Route path="/configuracoes" element={<ConfiguracoesPage />} />
        <Route path="/preferencias" element={<PreferenciasPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
