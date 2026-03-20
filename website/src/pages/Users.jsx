import { useState, useEffect } from 'react'
import { Search, Filter, ChevronDown, ChevronUp, Eye, AlertTriangle, Shield, TrendingUp } from 'lucide-react'
import RiskAnalysis from '../components/RiskAnalysis'
import { fetchRiskyUsers } from '../services/api'

// Risk level classification
const getRiskLevel = (score) => {
    if (score >= 400) return 'critical'
    if (score >= 250) return 'high'
    if (score >= 150) return 'medium'
    return 'low'
}

const getRiskColor = (level) => {
    switch (level) {
        case 'critical': return '#ef4444'
        case 'high': return '#f97316'
        case 'medium': return '#eab308'
        case 'low': return '#22c55e'
        default: return '#6b7280'
    }
}

function Users() {
    const [users, setUsers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [sortField, setSortField] = useState('total_risk_score')
    const [sortOrder, setSortOrder] = useState('desc')
    const [selectedRisk, setSelectedRisk] = useState('all')
    const [selectedUser, setSelectedUser] = useState(null)

    useEffect(() => {
        loadUsers()
    }, [])

    const loadUsers = async () => {
        try {
            setLoading(true)
            const data = await fetchRiskyUsers(100)

            if (data && data.length > 0) {
                // Enrich with risk levels
                const enrichedUsers = data.map((user, idx) => ({
                    ...user,
                    rank: idx + 1,
                    risk_level: getRiskLevel(user.total_risk_score)
                }))
                setUsers(enrichedUsers)
                setError(null)
            } else {
                throw new Error('No user data returned')
            }
        } catch (err) {
            setError('Unable to connect to API. Make sure the backend is running.')
            // Fallback mock data for demo
            setUsers([
                { user: 'U101', total_risk_score: 586.75, rank: 1, risk_level: 'critical' },
                { user: 'U111', total_risk_score: 516.99, rank: 2, risk_level: 'critical' },
                { user: 'U107', total_risk_score: 505.73, rank: 3, risk_level: 'critical' },
                { user: 'U112', total_risk_score: 448.38, rank: 4, risk_level: 'critical' },
                { user: 'U143', total_risk_score: 443.83, rank: 5, risk_level: 'critical' },
            ])
        } finally {
            setLoading(false)
        }
    }

    // Filter and sort users
    const filteredUsers = users
        .filter(user => {
            const matchesSearch = user.user.toLowerCase().includes(searchTerm.toLowerCase())
            const matchesRisk = selectedRisk === 'all' || user.risk_level === selectedRisk
            return matchesSearch && matchesRisk
        })
        .sort((a, b) => {
            const aVal = a[sortField]
            const bVal = b[sortField]
            return sortOrder === 'desc' ? bVal - aVal : aVal - bVal
        })

    const handleSort = (field) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
        } else {
            setSortField(field)
            setSortOrder('desc')
        }
    }

    const SortIcon = ({ field }) => {
        if (sortField !== field) return null
        return sortOrder === 'desc' ? <ChevronDown size={14} /> : <ChevronUp size={14} />
    }

    // Stats summary
    const stats = {
        total: users.length,
        critical: users.filter(u => u.risk_level === 'critical').length,
        high: users.filter(u => u.risk_level === 'high').length,
        medium: users.filter(u => u.risk_level === 'medium').length,
        low: users.filter(u => u.risk_level === 'low').length,
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
            {selectedUser && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 50,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(0,0,0,0.8)',
                    backdropFilter: 'blur(4px)',
                    padding: 16
                }}>
                    <RiskAnalysis userId={selectedUser} onClose={() => setSelectedUser(null)} />
                </div>
            )}

            {/* Header Stats */}
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
                    <AlertTriangle size={16} />
                    {error}
                </div>
            )}

            {/* Controls */}
            <div className="users-controls card">
                <div className="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div className="filter-group">
                    <Filter size={16} />
                    <select
                        value={selectedRisk}
                        onChange={(e) => setSelectedRisk(e.target.value)}
                    >
                        <option value="all">All Risk Levels</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>

            {/* Users Table */}
            <div className="card users-table-card">
                <div className="card-header">
                    <h3 className="card-title">User Risk Ranking</h3>
                    <span className="showing-count">{filteredUsers.length} users</span>
                </div>

                <div className="table-container">
                    <table className="users-table">
                        <thead>
                            <tr>
                                <th onClick={() => handleSort('rank')} className="sortable">
                                    Rank <SortIcon field="rank" />
                                </th>
                                <th>User ID</th>
                                <th onClick={() => handleSort('total_risk_score')} className="sortable">
                                    Risk Score <SortIcon field="total_risk_score" />
                                </th>
                                <th>Risk Level</th>
                                <th>Risk Distribution</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.map((user) => (
                                <tr key={user.user} className={`risk-row ${user.risk_level}`}>
                                    <td className="rank-cell">
                                        <span className={`rank-badge ${user.rank <= 3 ? 'top' : ''}`}>
                                            #{user.rank}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="user-id mono">{user.user}</span>
                                    </td>
                                    <td>
                                        <span className="risk-score" style={{ color: getRiskColor(user.risk_level) }}>
                                            {user.total_risk_score.toFixed(2)}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`risk-badge ${user.risk_level}`}>
                                            {user.risk_level}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="risk-bar-container">
                                            <div
                                                className="risk-bar"
                                                style={{
                                                    width: `${Math.min(100, (user.total_risk_score / 600) * 100)}%`,
                                                    background: `linear-gradient(90deg, ${getRiskColor(user.risk_level)}, ${getRiskColor(user.risk_level)}88)`
                                                }}
                                            />
                                        </div>
                                    </td>
                                    <td>
                                        <button
                                            className="btn-investigate"
                                            onClick={() => setSelectedUser(user.user)}
                                        >
                                            <Eye size={14} />
                                            Investigate
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default Users
