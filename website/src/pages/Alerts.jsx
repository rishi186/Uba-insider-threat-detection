import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Clock, Filter, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { fetchAlerts } from '../services/api'

const statusConfig = {
    open: { label: 'Open', bg: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-primary)' },
    investigating: { label: 'Investigating', bg: 'rgba(234, 179, 8, 0.15)', color: 'var(--risk-medium)' },
    closed: { label: 'Closed', bg: 'rgba(107, 114, 128, 0.15)', color: 'var(--text-muted)' },
    resolved: { label: 'Resolved', bg: 'rgba(34, 197, 94, 0.15)', color: 'var(--risk-low)' }
}

const severityMap = {
    Critical: 'critical',
    High: 'high',
    Medium: 'medium',
}

function Alerts() {
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [expandedId, setExpandedId] = useState(null)
    const [filter, setFilter] = useState('all')
    const [total, setTotal] = useState(0)

    // Fetch real alerts from backend
    const loadAlerts = async () => {
        setLoading(true)
        const data = await fetchAlerts({ limit: 200 })
        if (data && data.alerts) {
            // Map backend AlertItem → UI shape
            const mapped = data.alerts.map(a => ({
                id: a.alert_id,
                user: a.user,
                risk: severityMap[a.severity] || 'medium',
                severity: a.severity,
                score: Math.round(a.risk_score),
                action: a.activity || 'Anomalous Activity',
                description: a.mitre_tactic
                    ? `MITRE: ${a.mitre_tactic}${a.mitre_technique ? ` / ${a.mitre_technique}` : ''}`
                    : `Risk score: ${Math.round(a.risk_score)}`,
                time: a.timestamp || 'Unknown',
                timestamp: a.timestamp || '',
                status: a.status || 'open',
                mitre_tactic: a.mitre_tactic,
                mitre_technique: a.mitre_technique,
            }))
            setAlerts(mapped)
            setTotal(data.total || mapped.length)
        }
        setLoading(false)
    }

    useEffect(() => {
        loadAlerts()
    }, [])

    const filteredAlerts = filter === 'all'
        ? alerts
        : alerts.filter(a => a.status === filter)

    const updateStatus = (id, newStatus) => {
        setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: newStatus } : a))
    }

    const statCounts = {
        open: alerts.filter(a => a.status === 'open').length,
        investigating: alerts.filter(a => a.status === 'investigating').length,
        resolved: alerts.filter(a => a.status === 'resolved' || a.status === 'closed').length,
    }

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading alerts...</p>
            </div>
        )
    }

    return (
        <div>
            {/* Stats Row */}
            <div className="stats-grid" style={{ marginBottom: 24 }}>
                <div className="card stat-card">
                    <div className="stat-icon red">
                        <AlertTriangle size={24} />
                    </div>
                    <div>
                        <div className="stat-value">{statCounts.open}</div>
                        <div className="stat-label">Open Alerts</div>
                    </div>
                </div>
                <div className="card stat-card">
                    <div className="stat-icon amber">
                        <Clock size={24} />
                    </div>
                    <div>
                        <div className="stat-value">{statCounts.investigating}</div>
                        <div className="stat-label">Investigating</div>
                    </div>
                </div>
                <div className="card stat-card">
                    <div className="stat-icon green">
                        <CheckCircle size={24} />
                    </div>
                    <div>
                        <div className="stat-value">{statCounts.resolved}</div>
                        <div className="stat-label">Resolved</div>
                    </div>
                </div>
                <div className="card stat-card">
                    <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-primary)' }}>
                        <RefreshCw size={24} />
                    </div>
                    <div>
                        <div className="stat-value">{total}</div>
                        <div className="stat-label">Total Alerts</div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <Filter size={18} style={{ color: 'var(--text-muted)' }} />
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Filter:</span>
                    {['all', 'open', 'investigating', 'resolved', 'closed'].map(status => (
                        <button
                            key={status}
                            onClick={() => setFilter(status)}
                            style={{
                                padding: '6px 14px',
                                borderRadius: 20,
                                border: 'none',
                                background: filter === status ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                                color: filter === status ? 'white' : 'var(--text-secondary)',
                                fontSize: '0.8rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                textTransform: 'capitalize'
                            }}
                        >
                            {status}
                        </button>
                    ))}
                    <button
                        onClick={loadAlerts}
                        style={{
                            marginLeft: 'auto',
                            padding: '6px 14px',
                            borderRadius: 20,
                            border: '1px solid var(--border-primary)',
                            background: 'transparent',
                            color: 'var(--text-secondary)',
                            fontSize: '0.8rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6
                        }}
                    >
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
            </div>

            {/* Alert Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {filteredAlerts.length === 0 && (
                    <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        No alerts match this filter.
                    </div>
                )}
                {filteredAlerts.map(alert => (
                    <div key={alert.id} className="card" style={{
                        borderLeft: `4px solid ${alert.risk === 'critical' ? 'var(--risk-critical)' :
                            alert.risk === 'high' ? 'var(--risk-high)' :
                                alert.risk === 'medium' ? 'var(--risk-medium)' :
                                    'var(--risk-low)'
                            }`,
                        padding: 0
                    }}>
                        {/* Alert Header */}
                        <div
                            onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
                            style={{
                                padding: 16,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 16
                            }}
                        >
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                                    <span className="mono" style={{ fontWeight: 600 }}>{alert.user}</span>
                                    <span className={`risk-badge ${alert.risk}`}>{alert.severity}</span>
                                    <span style={{
                                        padding: '3px 10px',
                                        borderRadius: 12,
                                        fontSize: '0.7rem',
                                        fontWeight: 500,
                                        background: (statusConfig[alert.status] || statusConfig.open).bg,
                                        color: (statusConfig[alert.status] || statusConfig.open).color
                                    }}>
                                        {(statusConfig[alert.status] || statusConfig.open).label}
                                    </span>
                                </div>
                                <div style={{ fontWeight: 500, marginBottom: 2 }}>{alert.action}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{alert.description}</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{
                                    fontSize: '1.5rem',
                                    fontWeight: 700,
                                    color: alert.score >= 70 ? 'var(--risk-critical)' :
                                        alert.score >= 50 ? 'var(--risk-medium)' :
                                            'var(--text-secondary)'
                                }}>
                                    {alert.score}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{alert.time}</div>
                            </div>
                            {expandedId === alert.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </div>

                        {/* Expanded Details */}
                        {expandedId === alert.id && (
                            <div style={{
                                padding: '0 16px 16px',
                                borderTop: '1px solid var(--border-primary)',
                                marginTop: -1
                            }}>
                                <div style={{ paddingTop: 16, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Alert ID</div>
                                        <div className="mono" style={{ fontSize: '0.875rem' }}>{alert.id}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Severity</div>
                                        <div>{alert.severity}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Timestamp</div>
                                        <div className="mono" style={{ fontSize: '0.875rem' }}>{alert.timestamp || 'N/A'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>MITRE ATT&CK</div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                            {alert.mitre_tactic && alert.mitre_tactic !== 'nan' && (
                                                <span style={{
                                                    padding: '2px 8px',
                                                    borderRadius: 4,
                                                    background: 'var(--bg-tertiary)',
                                                    fontSize: '0.7rem'
                                                }}>
                                                    {alert.mitre_tactic}
                                                </span>
                                            )}
                                            {alert.mitre_technique && (
                                                <span style={{
                                                    padding: '2px 8px',
                                                    borderRadius: 4,
                                                    background: 'var(--bg-tertiary)',
                                                    fontSize: '0.7rem'
                                                }}>
                                                    {alert.mitre_technique}
                                                </span>
                                            )}
                                            {(!alert.mitre_tactic || alert.mitre_tactic === 'nan') && !alert.mitre_technique && (
                                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>N/A</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                                    <button
                                        className="btn btn-primary"
                                        style={{ padding: '8px 16px' }}
                                        onClick={() => updateStatus(alert.id, 'investigating')}
                                    >
                                        Investigate
                                    </button>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '8px 16px' }}
                                        onClick={() => updateStatus(alert.id, 'resolved')}
                                    >
                                        Mark Resolved
                                    </button>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '8px 16px' }}
                                        onClick={() => updateStatus(alert.id, 'closed')}
                                    >
                                        Dismiss
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

export default Alerts
