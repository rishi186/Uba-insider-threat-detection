import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import {
    Shield,
    LayoutDashboard,
    Activity,
    Users as UsersIcon,
    AlertTriangle,
    Search,
    Settings as SettingsIcon,
    Bell,
    Mouse
} from 'lucide-react'

// Pages
import Dashboard from './pages/Dashboard'
import RiskHeatmap from './pages/RiskHeatmap'
import Forensics from './pages/Forensics'
import Alerts from './pages/Alerts'
import Landing from './pages/Landing'
import Users from './pages/Users'
import Settings from './pages/Settings'
import MouseTracking from './pages/MouseTracking'
import MatrixBackground from './components/MatrixBackground'
import CustomCursor from './components/CustomCursor'
import TypewriterText from './components/TypewriterText'
import ToastSystem from './components/ToastSystem'
import ErrorBoundary from './components/ErrorBoundary'
import RoleGuard from './components/RoleGuard'
import { useRole } from './context/RoleContext'

function App() {
    const location = useLocation()
    const { role, setRole } = useRole()

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/': return 'Dashboard'
            case '/landing': return 'Project Overview'
            case '/heatmap': return 'Risk Heatmap'
            case '/forensics': return 'Forensics'
            case '/alerts': return 'Active Alerts'
            case '/mouse-tracking': return 'Mouse Biometrics'
            default: return 'Dashboard'
        }
    }

    return (
        <>
            <MatrixBackground />
            <CustomCursor />
            <ToastSystem />
            <div className="app-layout">
                {/* Sidebar */}
                <aside className="sidebar">
                    <div className="sidebar-header">
                        <div className="sidebar-logo">
                            <Shield />
                            <h1 className="glitch" data-text="UBA ITD">UBA ITD</h1>
                        </div>
                    </div>

                    <nav className="sidebar-nav">
                        <div className="nav-section">
                            <div className="nav-section-title">Overview</div>
                            <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <LayoutDashboard />
                                Dashboard
                            </NavLink>
                            <NavLink to="/heatmap" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <Activity />
                                Risk Heatmap
                            </NavLink>
                        </div>

                        <div className="nav-section">
                            <div className="nav-section-title">Investigation</div>
                            <NavLink to="/forensics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <Search />
                                Forensics
                            </NavLink>
                            <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <AlertTriangle />
                                Active Alerts
                            </NavLink>
                            <NavLink to="/mouse-tracking" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <Mouse />
                                Mouse Biometrics
                            </NavLink>
                        </div>

                        <div className="nav-section">
                            <div className="nav-section-title">System</div>
                            <NavLink to="/users" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <UsersIcon />
                                Users
                            </NavLink>
                            <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                                <SettingsIcon />
                                Settings
                            </NavLink>
                        </div>
                    </nav>
                </aside>

                {/* Header */}
                <header className="header">
                    <h2 className="header-title">
                        <TypewriterText text={getPageTitle()} key={location.pathname} />
                    </h2>
                    <div className="header-actions">
                        <div className="live-indicator">LIVE</div>
                        
                        {/* Role Switcher */}
                        <div className="role-switcher" style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--surface-color)', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ROLE:</span>
                            <select 
                                value={role} 
                                onChange={(e) => setRole(e.target.value)}
                                style={{ background: 'transparent', color: 'var(--text-primary)', border: 'none', outline: 'none', fontSize: '0.8rem', cursor: 'pointer' }}
                            >
                                <option value="Admin">Admin</option>
                                <option value="Analyst">Analyst</option>
                                <option value="Viewer">Viewer</option>
                            </select>
                        </div>
                        
                        <button className="btn btn-secondary" style={{ padding: '8px' }}>
                            <Bell size={18} />
                        </button>
                    </div>
                </header>

                {/* Main Content */}
                <main className="main-content">
                    <ErrorBoundary>
                        <Routes>
                            <Route path="/landing" element={<Landing />} />
                            <Route path="/" element={<Dashboard />} />
                            <Route path="/heatmap" element={<RiskHeatmap />} />
                            <Route path="/forensics" element={<Forensics />} />
                            <Route path="/alerts" element={<RoleGuard allowedRoles={['Admin', 'Analyst']}><Alerts /></RoleGuard>} />
                            <Route path="/users" element={<RoleGuard allowedRoles={['Admin', 'Analyst']}><Users /></RoleGuard>} />
                            <Route path="/settings" element={<RoleGuard allowedRoles={['Admin']}><Settings /></RoleGuard>} />
                            <Route path="/mouse-tracking" element={<MouseTracking />} />
                        </Routes>
                    </ErrorBoundary>
                </main>
            </div>
        </>
    )
}

export default App
