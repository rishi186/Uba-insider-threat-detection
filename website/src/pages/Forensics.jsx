import { useState, useEffect } from 'react'
import { Search, Download, Clock, FileText, Globe, Usb, Mail, Terminal, Lock, Unlock } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import RedactedText from '../components/RedactedText'
import NetworkMap from '../components/NetworkMap'
import { fetchUserProfile, fetchTimeline, fetchRiskyUsers } from '../services/api'

// Helper: classify activity type from event source/activity text
const classifyActivity = (event) => {
    const activity = (event.activity || '').toLowerCase()
    const type = (event.event_type || '').toLowerCase()
    if (type.includes('device') || activity.includes('usb') || activity.includes('connect')) return 'usb'
    if (type.includes('email') || activity.includes('email') || activity.includes('mail')) return 'email'
    if (type.includes('file') || activity.includes('file') || activity.includes('copy') || activity.includes('download')) return 'file'
    if (type.includes('http') || activity.includes('web') || activity.includes('http') || activity.includes('url')) return 'web'
    if (activity.includes('logon') || activity.includes('login') || activity.includes('logoff')) return 'login'
    return 'terminal'
}

// Helper function to get icon based on activity type
const getIcon = (type) => {
    switch (type) {
        case 'file': return <FileText size={16} />
        case 'usb': return <Usb size={16} />
        case 'web': return <Globe size={16} />
        case 'terminal': return <Terminal size={16} />
        case 'email': return <Mail size={16} />
        case 'login': return <Lock size={16} />
        default: return <Clock size={16} />
    }
}

// Helper function to get risk-based styling
const getRiskStyles = (riskScore) => {
    if (riskScore >= 80) {
        return { bg: 'rgba(239, 68, 68, 0.1)', color: 'var(--risk-critical)' }
    } else if (riskScore >= 60) {
        return { bg: 'rgba(249, 115, 22, 0.1)', color: 'var(--risk-high)' }
    } else if (riskScore >= 40) {
        return { bg: 'rgba(234, 179, 8, 0.1)', color: 'var(--risk-medium)' }
    } else {
        return { bg: 'rgba(34, 197, 94, 0.1)', color: 'var(--risk-low)' }
    }
}

// Category colors for the pie chart
const CATEGORY_COLORS = {
    file: '#06b6d4',
    login: '#f97316',
    usb: '#eab308',
    web: '#8b5cf6',
    email: '#22c55e',
    terminal: '#ec4899',
}

function Forensics() {
    const [searchQuery, setSearchQuery] = useState('')
    const [userData, setUserData] = useState(null)
    const [timelineEvents, setTimelineEvents] = useState([])
    const [hourlyRisk, setHourlyRisk] = useState([])
    const [anomalyBreakdown, setAnomalyBreakdown] = useState([])
    const [loading, setLoading] = useState(false)
    const [showPrivateData, setShowPrivateData] = useState(false)
    const [error, setError] = useState(null)

    // Load first user on mount
    useEffect(() => {
        const loadDefault = async () => {
            const users = await fetchRiskyUsers(1)
            if (users && users.length > 0) {
                setSearchQuery(users[0].user)
                investigate(users[0].user)
            }
        }
        loadDefault()
    }, [])

    const investigate = async (userId) => {
        if (!userId.trim()) return
        setLoading(true)
        setError(null)

        // Fetch profile
        const profile = await fetchUserProfile(userId.trim())
        if (!profile) {
            setError(`User "${userId}" not found. Make sure backend is running.`)
            setLoading(false)
            return
        }

        setUserData({
            userId: profile.user,
            name: profile.user,
            role: profile.role || 'Employee',
            department: profile.department || 'General',
            riskLevel: profile.risk_level || 'Low',
            riskScore: Math.round(profile.total_risk_score || 0),
            rank: profile.rank || '-',
        })

        // Fetch timeline
        const timelineData = await fetchTimeline(userId.trim(), 500, 0)
        if (timelineData && timelineData.events) {
            const events = timelineData.events.map(e => ({
                type: classifyActivity(e),
                action: e.activity || 'Unknown',
                details: `${e.event_type || 'Event'} — Risk: ${Math.round(e.risk_score)}${e.pc ? ` (${e.pc})` : ''}`,
                risk: Math.round(e.risk_score),
                time: e.timestamp || '',
                is_anomaly: e.is_anomaly,
            }))
            setTimelineEvents(events)

            // Compute anomaly breakdown from event types
            const typeCounts = {}
            events.forEach(e => {
                const t = e.type
                typeCounts[t] = (typeCounts[t] || 0) + 1
            })
            const breakdown = Object.entries(typeCounts).map(([name, value]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                value,
                color: CATEGORY_COLORS[name] || '#6b7280',
            }))
            setAnomalyBreakdown(breakdown)

            // Compute hourly risk pattern
            const hourBuckets = Array.from({ length: 24 }, () => [])
            events.forEach(e => {
                if (e.time) {
                    const hourMatch = e.time.match(/(\d{2}):\d{2}/)
                    if (hourMatch) {
                        const hour = parseInt(hourMatch[1], 10)
                        hourBuckets[hour].push(e.risk)
                    }
                }
            })
            const hourlyData = hourBuckets.map((risks, i) => ({
                hour: `${i.toString().padStart(2, '0')}:00`,
                risk: risks.length > 0 ? Math.round(risks.reduce((a, b) => a + b, 0) / risks.length) : 0,
            }))
            setHourlyRisk(hourlyData)
        }

        setLoading(false)
    }

    const handleSearch = () => investigate(searchQuery)
    const handleKeyDown = (e) => { if (e.key === 'Enter') handleSearch() }

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Investigating user...</p>
            </div>
        )
    }

    return (
        <div>
            {/* Search Bar */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', gap: 12 }}>
                    <div style={{
                        flex: 1,
                        position: 'relative',
                        display: 'flex',
                        alignItems: 'center'
                    }}>
                        <Search size={18} style={{
                            position: 'absolute',
                            left: 12,
                            color: 'var(--text-muted)'
                        }} />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Enter User ID (e.g. U105)..."
                            style={{
                                width: '100%',
                                padding: '12px 12px 12px 40px',
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-primary)',
                                borderRadius: 8,
                                color: 'var(--text-primary)',
                                fontSize: '0.875rem'
                            }}
                        />
                    </div>
                    <button className="btn btn-primary" onClick={handleSearch}>
                        <Search size={16} />
                        Investigate
                    </button>
                    {/* Data Reveal Toggle */}
                    <button
                        onClick={() => setShowPrivateData(!showPrivateData)}
                        className="btn btn-secondary"
                        style={{
                            padding: '12px',
                            color: showPrivateData ? 'var(--accent-primary)' : 'var(--text-muted)',
                            borderColor: showPrivateData ? 'var(--accent-primary)' : 'var(--border-primary)'
                        }}
                        title={showPrivateData ? "Encrypt Data" : "Decrypt Sensitive Data"}
                    >
                        {showPrivateData ? <Unlock size={18} /> : <Lock size={18} />}
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{
                    marginBottom: 24,
                    borderLeft: '4px solid var(--risk-critical)',
                    color: 'var(--risk-critical)'
                }}>
                    {error}
                </div>
            )}

            {userData && (
                <>
                    {/* User Profile Card */}
                    <div className="grid-3" style={{ marginBottom: 24 }}>
                        <div className="card" style={{ gridColumn: 'span 2' }}>
                            <div className="card-header">
                                <h3 className="card-title">User Profile</h3>
                                <button className="btn btn-secondary" style={{ padding: '6px 12px' }}>
                                    <Download size={14} />
                                    Export Report
                                </button>
                            </div>
                            <div style={{ display: 'flex', gap: 32 }}>
                                <div style={{
                                    width: 80,
                                    height: 80,
                                    borderRadius: '50%',
                                    background: 'linear-gradient(135deg, var(--accent-primary), #a78bfa)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '1.5rem',
                                    fontWeight: 700
                                }}>
                                    {userData.userId.slice(0, 2)}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <h2 style={{ marginBottom: 4 }}>{userData.userId}</h2>
                                    <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                                        {userData.role} • {userData.department}
                                    </p>
                                    <div style={{ display: 'flex', gap: 24 }}>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>User ID</div>
                                            <div className="mono" style={{ fontWeight: 500 }}>{userData.userId}</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Rank</div>
                                            <div>#{userData.rank}</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Risk Level</div>
                                            <span className={`risk-badge ${userData.riskLevel.toLowerCase()}`}>
                                                {userData.riskLevel}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{
                                        fontSize: '3rem',
                                        fontWeight: 700,
                                        color: userData.riskScore >= 60 ? 'var(--risk-high)' : 'var(--risk-low)',
                                        lineHeight: 1
                                    }}>
                                        {userData.riskScore}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Risk Score</div>
                                </div>
                            </div>
                        </div>

                        {/* Anomaly Breakdown */}
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: 16 }}>Activity Breakdown</h3>
                            <div style={{ height: 180 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={anomalyBreakdown}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={40}
                                            outerRadius={70}
                                            dataKey="value"
                                        >
                                            {anomalyBreakdown.map((entry, idx) => (
                                                <Cell key={idx} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{
                                                background: '#1f2937',
                                                border: '1px solid #374151',
                                                borderRadius: 8
                                            }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                                {anomalyBreakdown.map(item => (
                                    <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <div style={{ width: 8, height: 8, borderRadius: 2, background: item.color }} />
                                        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{item.name}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Network Graph */}
                    <div style={{ marginBottom: 24 }}>
                        <NetworkMap />
                    </div>

                    {/* Activity Timeline & Hourly Chart */}
                    <div className="grid-2">
                        {/* Timeline */}
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">Activity Timeline</h3>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    {timelineEvents.length} events
                                </span>
                            </div>
                            <div className="activity-feed" style={{ maxHeight: 400, overflowY: 'auto' }}>
                                {timelineEvents.slice(0, 50).map((event, idx) => {
                                    const styles = getRiskStyles(event.risk)
                                    return (
                                        <div key={idx} className="activity-item" style={{
                                            background: styles.bg,
                                            borderRadius: 8,
                                            padding: 12,
                                            marginBottom: 8,
                                            border: `1px solid ${styles.bg}`
                                        }}>
                                            <div style={{
                                                width: 32,
                                                height: 32,
                                                borderRadius: 8,
                                                background: 'var(--bg-tertiary)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                color: styles.color
                                            }}>
                                                {getIcon(event.type)}
                                            </div>
                                            <div className="activity-content" style={{ flex: 1 }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                    <div>
                                                        <div className="activity-title">{event.action}</div>
                                                        <div className="activity-meta">
                                                            <RedactedText text={event.details} revealed={showPrivateData} />
                                                        </div>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <div style={{
                                                            fontWeight: 600,
                                                            color: styles.color,
                                                            fontSize: '0.875rem'
                                                        }}>
                                                            {event.risk}
                                                        </div>
                                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{event.time}</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })}
                                {timelineEvents.length === 0 && (
                                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20 }}>
                                        No events found for this user.
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Hourly Risk Chart */}
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">Hourly Risk Pattern</h3>
                            </div>
                            <div className="chart-container">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={hourlyRisk}>
                                        <XAxis
                                            dataKey="hour"
                                            stroke="#6b7280"
                                            fontSize={10}
                                            tickFormatter={(v) => v.split(':')[0]}
                                        />
                                        <YAxis stroke="#6b7280" fontSize={10} domain={[0, 100]} />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#1f2937',
                                                border: '1px solid #374151',
                                                borderRadius: 8
                                            }}
                                        />
                                        <Bar
                                            dataKey="risk"
                                            fill="#06b6d4"
                                            radius={[4, 4, 0, 0]}
                                        />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

export default Forensics
