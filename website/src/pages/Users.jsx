import { useState, useEffect } from 'react'
import { Search, Filter, ChevronDown, ChevronUp, Eye, AlertTriangle, Shield, TrendingUp, Clock, File, Usb, Globe, Mail } from 'lucide-react'
import RiskAnalysis from '../components/RiskAnalysis'
import { fetchRiskyUsers } from '../services/api'

// Risk level classification (aligned with backend Z-score thresholds)
const getRiskLevel = (score) => {
    if (score >= 80) return 'critical'
    if (score >= 50) return 'high'
    if (score >= 25) return 'medium'
    return 'low'
}

const getRiskColor = (level) => {
    switch (level) {
        case 'critical': return '#ef4444'
        case 'high':     return '#f97316'
        case 'medium':   return '#eab308'
        case 'low':      return '#22c55e'
        default:         return '#6b7280'
    }
}

const getRiskGradient = (level) => {
    switch (level) {
        case 'critical': return 'linear-gradient(135deg, #ef444420, #ef444408)'
        case 'high':     return 'linear-gradient(135deg, #f9731620, #f9731608)'
        case 'medium':   return 'linear-gradient(135deg, #eab30820, #eab30808)'
        case 'low':      return 'linear-gradient(135deg, #22c55e20, #22c55e08)'
        default:         return 'transparent'
    }
}

// Format login hour to readable time
const formatHour = (h) => {
    if (h == null) return '—'
    const hour = Math.floor(h)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const display = hour % 12 === 0 ? 12 : hour % 12
    return `${display}:00 ${ampm}`
}

function Users() {
    const [users, setUsers]             = useState([])
    const [loading, setLoading]         = useState(true)
    const [error, setError]             = useState(null)
    const [searchTerm, setSearchTerm]   = useState('')
    const [sortField, setSortField]     = useState('total_risk_score')
    const [sortOrder, setSortOrder]     = useState('desc')
    const [selectedRisk, setSelectedRisk] = useState('all')
    const [selectedUser, setSelectedUser] = useState(null)
    const [expandedRow, setExpandedRow]   = useState(null)

    useEffect(() => {
        loadUsers()
    }, [])

    const loadUsers = async () => {
        try {
            setLoading(true)
            const data = await fetchRiskyUsers()   // default limit=500 → all users

            if (data && data.length > 0) {
                const enrichedUsers = data.map((user, idx) => ({
                    ...user,
                    rank: idx + 1,
                    risk_level: user.risk_level ? user.risk_level.toLowerCase() : getRiskLevel(user.total_risk_score)
                }))
                setUsers(enrichedUsers)
                setError(null)
            } else {
                throw new Error('No user data returned')
            }
        } catch (err) {
            setError('Unable to connect to API. Make sure the backend is running.')
            // Realistic fallback mock data (0-100 scale, enriched fields)
            setUsers(generateMockUsers())
        } finally {
            setLoading(false)
        }
    }

    // Generate rich mock data for offline demo
    const generateMockUsers = () => {
        const depts = ['Engineering','Finance','HR','Sales','IT','Legal','Executive','Marketing','Operations','Research']
        const roles = ['Employee','Admin','Contractor']
        const locs  = ['New York','San Francisco','Austin','Chicago','Seattle','London','Remote']
        return Array.from({ length: 125 }, (_, i) => {
            const uid = `U${100 + i}`
            const score = i === 5 ? 117.1 : Math.max(0, 60 - i * 0.9 + (Math.random() * 10 - 5))
            const level = getRiskLevel(score)
            return {
                user: uid, rank: i + 1,
                total_risk_score: parseFloat(score.toFixed(2)),
                risk_level: level,
                role: roles[i % 3],
                department: depts[i % depts.length],
                location: locs[i % locs.length],
                avg_login_hour: level === 'critical' ? 2.5 : level === 'high' ? 20 : 8.5 + (i % 3),
                avg_session_duration_hrs: 7 + (i % 3),
                failed_logins: level === 'critical' ? 8 : level === 'high' ? 3 : i % 2,
                after_hours_logins: level === 'critical' ? 12 : level === 'high' ? 4 : i % 3,
                file_copies: level === 'critical' ? 25 : level === 'high' ? 8 : i % 4,
                usb_events: level === 'critical' ? 10 : level === 'high' ? 3 : 0,
                confidential_files: level === 'critical' ? 15 : level === 'high' ? 4 : 0,
                suspicious_urls: level === 'critical' ? 12 : level === 'high' ? 5 : 0,
                large_emails: level === 'critical' ? 8 : level === 'high' ? 3 : 0,
                external_emails: level === 'critical' ? 20 : level === 'high' ? 6 : i % 3,
                event_count: 40 + (i % 80),
                anomaly_score: parseFloat(Math.min(1, score / 100).toFixed(3)),
                deviation_sigma: parseFloat((score / 17).toFixed(2)),
                last_active: `2024-03-${String(Math.max(1, 30 - (i % 7))).padStart(2, '0')}`,
                mitre_tactics: level === 'critical' ? 'TA0010-Exfiltration|TA0011-C2' : level === 'high' ? 'TA0010-Exfiltration' : '',
            }
        })
    }

    // Filter and sort
    const filteredUsers = users
        .filter(u => {
            const matchSearch = u.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (u.department || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                (u.role || '').toLowerCase().includes(searchTerm.toLowerCase())
            const matchRisk = selectedRisk === 'all' || u.risk_level === selectedRisk
            return matchSearch && matchRisk
        })
        .sort((a, b) => {
            const aVal = a[sortField] ?? 0
            const bVal = b[sortField] ?? 0
            if (typeof aVal === 'string') return sortOrder === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal)
            return sortOrder === 'desc' ? bVal - aVal : aVal - bVal
        })

    const handleSort = (field) => {
        if (sortField === field) setSortOrder(o => o === 'desc' ? 'asc' : 'desc')
        else { setSortField(field); setSortOrder('desc') }
    }

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span style={{ opacity: 0.3, fontSize: 10 }}>↕</span>
        return sortOrder === 'desc' ? <ChevronDown size={13} /> : <ChevronUp size={13} />
    }

    const stats = {
        total:    users.length,
        critical: users.filter(u => u.risk_level === 'critical').length,
        high:     users.filter(u => u.risk_level === 'high').length,
        medium:   users.filter(u => u.risk_level === 'medium').length,
        low:      users.filter(u => u.risk_level === 'low').length,
    }

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading user risk data...</p>
            </div>
        )
    }

    return (
        <div className="users-page relative">
            {/* Risk Analysis modal */}
            {selectedUser && (
                <div style={{
                    position: 'fixed', inset: 0, zIndex: 50,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(4px)', padding: 16
                }}>
                    <RiskAnalysis userId={selectedUser} onClose={() => setSelectedUser(null)} />
                </div>
            )}

            {/* ── Summary stat bar ── */}
            <div className="users-stats-bar">
                <div className="users-stat">
                    <Shield size={20} />
                    <span className="stat-number">{stats.total}</span>
                    <span className="stat-label">Total Users</span>
                </div>
                <div className="users-stat critical">
                    <AlertTriangle size={20} />
                    <span className="stat-number">{stats.critical}</span>
                    <span className="stat-label">Critical</span>
                </div>
                <div className="users-stat high">
                    <TrendingUp size={20} />
                    <span className="stat-number">{stats.high}</span>
                    <span className="stat-label">High Risk</span>
                </div>
                <div className="users-stat medium">
                    <span className="stat-number">{stats.medium}</span>
                    <span className="stat-label">Medium</span>
                </div>
                <div className="users-stat low">
                    <span className="stat-number">{stats.low}</span>
                    <span className="stat-label">Low</span>
                </div>
            </div>

            {error && (
                <div className="error-banner">
                    <AlertTriangle size={16} /> {error}
                </div>
            )}

            {/* ── Controls ── */}
            <div className="users-controls card">
                <div className="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Search by user ID, department, or role…"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="filter-group">
                    <Filter size={16} />
                    <select value={selectedRisk} onChange={e => setSelectedRisk(e.target.value)}>
                        <option value="all">All Risk Levels</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-secondary)' }}>
                    {filteredUsers.length} of {users.length} users
                </span>
            </div>

            {/* ── User Table ── */}
            <div className="card users-table-card">
                <div className="card-header">
                    <h3 className="card-title">User Risk Ranking &amp; Metrics</h3>
                </div>

                <div className="table-container">
                    <table className="users-table" style={{ fontSize: 13 }}>
                        <thead>
                            <tr>
                                <th onClick={() => handleSort('rank')} className="sortable">Rank <SortIcon field="rank" /></th>
                                <th>User ID</th>
                                <th>Dept / Role</th>
                                <th onClick={() => handleSort('total_risk_score')} className="sortable">Risk Score <SortIcon field="total_risk_score" /></th>
                                <th>Level</th>
                                <th onClick={() => handleSort('after_hours_logins')} className="sortable" title="After-hours logins">
                                    <Clock size={13} style={{ display:'inline', marginRight:3 }} />Logins
                                </th>
                                <th onClick={() => handleSort('file_copies')} className="sortable" title="File copies">
                                    <File size={13} style={{ display:'inline', marginRight:3 }} />Files
                                </th>
                                <th onClick={() => handleSort('usb_events')} className="sortable" title="USB events">
                                    <Usb size={13} style={{ display:'inline', marginRight:3 }} />USB
                                </th>
                                <th onClick={() => handleSort('suspicious_urls')} className="sortable" title="Suspicious URLs">
                                    <Globe size={13} style={{ display:'inline', marginRight:3 }} />URLs
                                </th>
                                <th onClick={() => handleSort('external_emails')} className="sortable" title="External emails">
                                    <Mail size={13} style={{ display:'inline', marginRight:3 }} />Emails
                                </th>
                                <th>σ Deviation</th>
                                <th>Bar</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.map((user) => {
                                const color = getRiskColor(user.risk_level)
                                const isExpanded = expandedRow === user.user
                                return (
                                    <>
                                        <tr
                                            key={user.user}
                                            className={`risk-row ${user.risk_level}`}
                                            style={{ background: isExpanded ? getRiskGradient(user.risk_level) : undefined }}
                                        >
                                            <td className="rank-cell">
                                                <span className={`rank-badge ${user.rank <= 3 ? 'top' : ''}`}>
                                                    #{user.rank}
                                                </span>
                                            </td>
                                            <td>
                                                <span className="user-id mono">{user.user}</span>
                                            </td>
                                            <td>
                                                <div style={{ lineHeight: 1.3 }}>
                                                    <div style={{ fontSize: 12, fontWeight: 600 }}>{user.department || '—'}</div>
                                                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{user.role || '—'}</div>
                                                </div>
                                            </td>
                                            <td>
                                                <span className="risk-score" style={{ color, fontWeight: 700 }}>
                                                    {user.total_risk_score.toFixed(1)}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`risk-badge ${user.risk_level}`}>
                                                    {user.risk_level}
                                                </span>
                                            </td>
                                            {/* After-hours logins */}
                                            <td>
                                                <span style={{ color: user.after_hours_logins > 3 ? '#ef4444' : user.after_hours_logins > 0 ? '#f97316' : 'var(--text-secondary)', fontWeight: user.after_hours_logins > 3 ? 700 : 400 }}>
                                                    {user.after_hours_logins ?? 0}
                                                </span>
                                            </td>
                                            {/* File copies */}
                                            <td>
                                                <span style={{ color: user.file_copies > 10 ? '#ef4444' : user.file_copies > 4 ? '#f97316' : 'var(--text-secondary)' }}>
                                                    {user.file_copies ?? 0}
                                                </span>
                                            </td>
                                            {/* USB events */}
                                            <td>
                                                <span style={{ color: user.usb_events > 5 ? '#ef4444' : user.usb_events > 1 ? '#f97316' : 'var(--text-secondary)', fontWeight: user.usb_events > 5 ? 700 : 400 }}>
                                                    {user.usb_events ?? 0}
                                                </span>
                                            </td>
                                            {/* Suspicious URLs */}
                                            <td>
                                                <span style={{ color: user.suspicious_urls > 5 ? '#ef4444' : user.suspicious_urls > 0 ? '#eab308' : 'var(--text-secondary)' }}>
                                                    {user.suspicious_urls ?? 0}
                                                </span>
                                            </td>
                                            {/* External emails */}
                                            <td>
                                                <span style={{ color: user.external_emails > 10 ? '#f97316' : 'var(--text-secondary)' }}>
                                                    {user.external_emails ?? 0}
                                                </span>
                                            </td>
                                            {/* σ deviation */}
                                            <td>
                                                <span style={{ color: user.deviation_sigma > 4 ? '#ef4444' : user.deviation_sigma > 2 ? '#f97316' : 'var(--text-secondary)', fontFamily: 'monospace', fontSize: 12 }}>
                                                    {user.deviation_sigma != null ? user.deviation_sigma.toFixed(2) : '—'}σ
                                                </span>
                                            </td>
                                            {/* Risk bar */}
                                            <td style={{ minWidth: 90 }}>
                                                <div className="risk-bar-container">
                                                    <div
                                                        className="risk-bar"
                                                        style={{
                                                            width: `${Math.min(100, user.total_risk_score)}%`,
                                                            background: `linear-gradient(90deg, ${color}, ${color}88)`
                                                        }}
                                                    />
                                                </div>
                                            </td>
                                            {/* Actions */}
                                            <td>
                                                <div style={{ display: 'flex', gap: 6 }}>
                                                    <button
                                                        className="btn-investigate"
                                                        onClick={() => setSelectedUser(user.user)}
                                                    >
                                                        <Eye size={13} /> Investigate
                                                    </button>
                                                    <button
                                                        style={{ background: 'transparent', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}
                                                        onClick={() => setExpandedRow(isExpanded ? null : user.user)}
                                                    >
                                                        {isExpanded ? '▲' : '▼'}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Expanded detail row */}
                                        {isExpanded && (
                                            <tr key={`${user.user}-expanded`} style={{ background: getRiskGradient(user.risk_level) }}>
                                                <td colSpan={13} style={{ padding: '12px 20px' }}>
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                                                        <MetricTile label="Location"         value={user.location || '—'} />
                                                        <MetricTile label="Avg Login Time"   value={formatHour(user.avg_login_hour)} highlight={user.avg_login_hour < 6 || user.avg_login_hour > 20} />
                                                        <MetricTile label="Session Duration" value={`${user.avg_session_duration_hrs ?? '—'}h`} />
                                                        <MetricTile label="Failed Logins"    value={user.failed_logins ?? 0} highlight={user.failed_logins > 3} />
                                                        <MetricTile label="Confidential Files" value={user.confidential_files ?? 0} highlight={user.confidential_files > 3} />
                                                        <MetricTile label="Total HTTP Reqs"  value={user.total_http_requests ?? 0} />
                                                        <MetricTile label="External Domains" value={user.external_domains ?? 0} highlight={user.external_domains > 5} />
                                                        <MetricTile label="Large Emails"     value={user.large_emails ?? 0} highlight={user.large_emails > 3} />
                                                        <MetricTile label="Total Events"     value={user.event_count ?? 0} />
                                                        <MetricTile label="Anomaly Score"    value={user.anomaly_score != null ? user.anomaly_score.toFixed(3) : '—'} highlight={user.anomaly_score > 0.7} />
                                                        <MetricTile label="Last Active"      value={user.last_active || '—'} />
                                                        <MetricTile label="MITRE Tactics"    value={user.mitre_tactics ? user.mitre_tactics.split('|').join(', ') : 'None'} highlight={!!user.mitre_tactics} />
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

// Small metric tile for the expanded row
function MetricTile({ label, value, highlight = false }) {
    return (
        <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: 8,
            padding: '8px 12px',
            border: highlight ? '1px solid #ef444440' : '1px solid var(--border)',
        }}>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: highlight ? '#ef4444' : 'var(--text-primary)' }}>{value}</div>
        </div>
    )
}

export default Users
