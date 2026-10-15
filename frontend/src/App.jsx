import { NavLink, Route, Routes } from 'react-router-dom'
import { useApi } from './api/useApi'
import Analytics from './pages/Analytics'
import AuditLog from './pages/AuditLog'
import Customers from './pages/Customers'
import Dashboard from './pages/Dashboard'
import DataQuality from './pages/DataQuality'
import EtlMonitoring from './pages/EtlMonitoring'
import Orders from './pages/Orders'
import Payments from './pages/Payments'
import Products from './pages/Products'

const NAV = [
  ['/', 'Dashboard', Dashboard],
  ['/customers', 'Customers', Customers],
  ['/products', 'Products', Products],
  ['/orders', 'Orders', Orders],
  ['/payments', 'Payments', Payments],
  ['/etl', 'ETL Monitoring', EtlMonitoring],
  ['/data-quality', 'Data Quality', DataQuality],
  ['/analytics', 'Analytics', Analytics],
  ['/audit', 'Audit Log', AuditLog],
]

function ApiStatus() {
  const { data, error } = useApi('/health')
  if (error) return <div className="api-status down">● API / database offline</div>
  if (!data) return <div className="api-status">● connecting…</div>
  return <div className="api-status up">● MySQL {data.mysql_version} connected</div>
}

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <strong>Enterprise Data Platform</strong>
          <span>Data management &amp; analytics</span>
        </div>
        <nav>
          {NAV.map(([path, label]) => (
            <NavLink key={path} to={path} end={path === '/'}>{label}</NavLink>
          ))}
        </nav>
        <ApiStatus />
      </aside>
      <main className="content">
        <Routes>
          {NAV.map(([path, , Page]) => <Route key={path} path={path} element={<Page />} />)}
        </Routes>
      </main>
    </div>
  )
}
