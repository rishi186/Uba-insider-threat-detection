import { useState, useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts'
import { Shield, AlertTriangle, Users, Activity, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import DecryptText from '../components/DecryptText'
import TiltCard from '../components/TiltCard'
import { fetchDashboardSummary, fetchRiskyUsers } from '../services/api'

function Dashboard() {
    const [stats, setStats] = useState({
        total_events: 0,
        high_risk_events: 0,
        avg_risk_score: 0,
        total_users: 0
    })
    const [alerts, setAlerts] = useState([])
    const [userRiskData, setUserRiskData] = useState([])
    const [loading, setLoading] = useState(true)
    const [lastUpdated, setLastUpdated] = useState(null)
    const refreshInterval = useRef(null)

    const REFRESH_SECONDS = 30

    // Data loading function (reusable for auto-refresh)
    const loadData = async (isAutoRefresh = false) => {
        if (!isAutoRefresh) setLoading(true)

        // Use the single dashboard summary endpoint
        const summary = await fetchDashboardSummary()
        if (summary) {
            setStats(prev => ({
                ...prev,
                ...summary.stats,
            }))

            // Build chart data from top risky users
            const topUsers = summary.top_risky_users || []
            if (topUsers.length > 0) {
                const chartPoints = topUsers.map(u => ({
                    user: u.user,
                    riskScore: Math.round(u.total_risk_score),
                    riskLevel: (u.risk_level && u.risk_level.toLowerCase()) || getRiskLevel(u.total_risk_score)
                }))
                setUserRiskData(chartPoints)

                const topAlerts = topUsers.slice(0, 8).map((u, idx) => ({
                    id: idx + 1,
                    user: u.user,
                    risk: (u.risk_level && u.risk_level.toLowerCase()) || getRiskLevel(u.total_risk_score),
                    action: getRiskAction(u.total_risk_score),
                    score: Math.round(u.total_risk_score),
                    department: u.department || 'General',
                    role: u.role || 'Employee'
                }))
                setAlerts(topAlerts)
            }
        } else {
            // Fallback: fetch individually
            const usersData = await fetchRiskyUsers(50)
            if (usersData && usersData.length > 0) {
                const chartPoints = usersData.map(u => ({
                    user: u.user,
                    riskScore: Math.round(u.total_risk_score),
                    riskLevel: (u.risk_level && u.risk_level.toLowerCase()) || getRiskLevel(u.total_risk_score)
                }))
                setUserRiskData(chartPoints)
            }
        }

        setLastUpdated(new Date())
        setLoading(false)
    }

    // Initial load + WebSockets + auto-refresh
    useEffect(() => {
        loadData()

        const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws') + '/api/ws/streams';
        const ws = new WebSocket(wsUrl);
        
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'biometric_update') {
                    // Real-time optimistic update of risk scores based on incoming biometric anomalies
                    setUserRiskData(prev => {
                        const updated = [...prev];
                        const idx = updated.findIndex(u => u.user === msg.data.user_id);
                        if (idx >= 0) {
                            // Scale the 0-100 anomaly score to the 0-100 risk score scale for visualization
                            const impliedRisk = msg.data.anomaly_score * 100;
                            if (impliedRisk > updated[idx].riskScore) {
                                updated[idx].riskScore = Math.round(impliedRisk);
                                updated[idx].riskLevel = getRiskLevel(updated[idx].riskScore);
                            }
                        }
                        return updated.sort((a,b) => b.riskScore - a.riskScore);
                    });
                }
            } catch (err) {
                console.error("Dashboard WS parsing error", err);
            }
        };

        refreshInterval.current = setInterval(() => loadData(true), REFRESH_SECONDS * 1000)
        
        return () => {
            clearInterval(refreshInterval.current);
            ws.close();
        };
    }, [])

    const getRiskLevel = (score) => {
        if (score >= 80) return 'critical'
        if (score >= 50) return 'high'
        if (score >= 25) return 'medium'
        return 'low'
    }

    const getRiskAction = (score) => {
        if (score >= 90) return 'Multiple High-Risk Activities'
        if (score >= 80) return 'Anomalous Behavior Pattern'
        if (score >= 60) return 'Elevated Activity Detected'
        if (score >= 40) return 'Above-Average Risk Profile'
        if (score >= 25) return 'Moderate Risk Indicators'
        return 'Normal Activity'
    }

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading dashboard data...</p>
            </div>
        )
    }

    return (
        <div>
            {/* Stats Grid */}
            <div className="stats-grid">
                <TiltCard className="card stat-card">
                    <div className="stat-icon cyan">
                        <Activity size={24} />
                    </div>
                    <div>
                        <div className="stat-value">
                            <DecryptText text={stats.total_events?.toLocaleString() || '—'} />
                        </div>
                        <div className="stat-label">Total Events</div>
                    </div>
                </TiltCard>

                <TiltCard className="card stat-card">
                    <div className="stat-icon red">
                        <AlertTriangle size={24} />
                    </div>
                    <div>
                        <div className="stat-value">
                            <DecryptText text={stats.high_risk_events || '—'} />
                        </div>
                        <div className="stat-label">High Risk Events</div>
                        <div className="stat-change up">
                            <TrendingUp size={12} style={{ display: 'inline', marginRight: 4 }} />
                            Needs attention
                        </div>
                    </div>
                </TiltCard>

                <TiltCard className="card stat-card">
                    <div className="stat-icon amber">
                        <Shield size={24} />
                    </div>
                    <div>
                        <div className="stat-value">
                            <DecryptText text={Math.round(stats.avg_risk_score || 0)} />
                        </div>
                        <div className="stat-label">Avg Risk Score</div>
                    </div>
                </TiltCard>

                <TiltCard className="card stat-card">
                    <div className="stat-icon green">
                        <Users size={24} />
                    </div>
                    <div>
                        <div className="stat-value">
                            <DecryptText text={stats.total_users?.toLocaleString() || '—'} />
                        </div>
                        <div className="stat-label">Users Monitored</div>
                        <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
                            All departments
                        </div>
                    </div>
                </TiltCard>
            </div>

            {/* Dashboard Content Grid */}
            <div className="dashboard-grid">
                {/* Left Column: Recent Alerts */}
                <div className="dashboard-left">
                    <div className="card" style={{ height: '100%' }}>
                        <div className="card-header">
                            <h3 className="card-title">Top Risk Users</h3>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {alerts.length} users
                            </span>
                        </div>
                        <div className="table-container">
                            <table style={{ fontSize: '0.8rem' }}>
                                <thead>
                                    <tr>
                                        <th>User</th>
                                        <th>Risk</th>
                                        <th>Score</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {alerts.map(alert => (
                                        <tr key={alert.id}>
                                            <td>
                                                <div style={{ fontWeight: 500 }}>{alert.user}</div>
                                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{alert.action}</div>
                                            </td>
                                            <td>
                                                <span className={`risk-badge ${alert.risk}`} style={{ padding: '2px 8px', fontSize: '0.65rem' }}>
                                                    {alert.risk}
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{
                                                    fontWeight: 600,
                                                    color: alert.score >= 80 ? 'var(--risk-critical)' :
                                                        alert.score >= 50 ? 'var(--risk-high)' :
                                                            alert.score >= 25 ? 'var(--risk-medium)' :
                                                                'var(--text-secondary)'
                                                }}>
                                                    {alert.score}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Right Column: Charts */}
                <div className="dashboard-main">
                    <div className="card scan-effect">
                        <div className="scan-container">
                            <div className="scanner-line"></div>
                            <div className="card-header">
                                <h3 className="card-title">User Risk Distribution</h3>
                            </div>
                            <div className="chart-container">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={userRiskData}>
                                        <defs>
                                            <linearGradient id="riskBarGradient" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.8} />
                                                <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.2} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis dataKey="user" stroke="#6b7280" fontSize={10} angle={-45} textAnchor="end" height={50} />
                                        <YAxis stroke="#6b7280" fontSize={11} />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#1f2937',
                                                border: '1px solid #374151',
                                                borderRadius: 8
                                            }}
                                            formatter={(value) => [`${value}`, 'Risk Score']}
                                        />
                                        <Bar
                                            dataKey="riskScore"
                                            fill="url(#riskBarGradient)"
                                            radius={[4, 4, 0, 0]}
                                        />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Risk Score Ranking (Top Users)</h3>
                        </div>
                        <div className="chart-container">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={userRiskData.slice(0, 20)}>
                                    <defs>
                                        <linearGradient id="riskAreaGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#f97316" stopOpacity={0.4} />
                                            <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="user" stroke="#6b7280" fontSize={10} angle={-45} textAnchor="end" height={50} />
                                    <YAxis stroke="#6b7280" fontSize={11} />
                                    <Tooltip
                                        contentStyle={{
                                            background: '#1f2937',
                                            border: '1px solid #374151',
                                            borderRadius: 8
                                        }}
                                        formatter={(value) => [`${value}`, 'Risk Score']}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="riskScore"
                                        stroke="#f97316"
                                        fill="url(#riskAreaGradient)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
