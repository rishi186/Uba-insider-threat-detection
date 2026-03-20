import { useState, useEffect } from 'react'
import { Calendar, Filter } from 'lucide-react'
import SystemTerminal from '../components/SystemTerminal'
import { fetchRiskyUsers } from '../services/api'

// Generate heatmap data (users x time slots)
const generateHeatmapData = () => {
    const users = ['U0124', 'U0234', 'U0512', 'U0734', 'U0847', 'U0923', 'U1024', 'U1128', 'U1256', 'U1337']
    const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`)

    return users.map(user => ({
        user,
        role: ['Admin', 'Engineer', 'Analyst', 'Manager', 'Employee'][Math.floor(Math.random() * 5)],
        department: ['IT', 'Finance', 'HR', 'R&D', 'Operations'][Math.floor(Math.random() * 5)],
        data: hours.map(hour => ({
            hour,
            risk: Math.random() > 0.85 ? Math.floor(Math.random() * 40) + 60 : // High risk (rare)
                Math.random() > 0.7 ? Math.floor(Math.random() * 30) + 30 :  // Medium risk
                    Math.floor(Math.random() * 30)                                // Low risk
        }))
    }))
}

const getRiskColor = (score) => {
    if (score >= 80) return 'rgba(239, 68, 68, 0.9)'
    if (score >= 60) return 'rgba(249, 115, 22, 0.8)'
    if (score >= 40) return 'rgba(234, 179, 8, 0.7)'
    if (score >= 20) return 'rgba(34, 197, 94, 0.4)'
    return 'rgba(75, 85, 99, 0.2)'
}

function RiskHeatmap() {
    const [heatmapData, setHeatmapData] = useState(generateHeatmapData())
    const [selectedCell, setSelectedCell] = useState(null)

    useEffect(() => {
        const loadUsers = async () => {
            const users = await fetchRiskyUsers(20)
            if (users && users.length > 0) {
                const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`)

                const mappedData = users.map(u => ({
                    user: u.user,
                    role: u.role || 'Unknown',
                    department: u.department || 'Unknown',
                    data: hours.map(hour => {
                        // Synthesize hourly risk pattern based on total risk score
                        // Higher total score means more frequent high-risk hours
                        const baseRisk = u.total_risk_score || 0
                        const volatility = Math.random()
                        let cellRisk

                        if (baseRisk > 70) {
                            // High risk user: often high, sometimes medium
                            cellRisk = volatility > 0.3 ? baseRisk + Math.random() * 10 : baseRisk - 20
                        } else if (baseRisk > 40) {
                            // Medium risk user
                            cellRisk = volatility > 0.6 ? baseRisk + 10 : Math.random() * 30
                        } else {
                            // Low risk user
                            cellRisk = volatility > 0.9 ? baseRisk + 20 : Math.random() * 10
                        }

                        return {
                            hour,
                            risk: Math.max(0, Math.min(100, Math.floor(cellRisk)))
                        }
                    })
                }))
                setHeatmapData(mappedData)
            }
        }
        loadUsers()
    }, [])

    const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}`)

    return (
        <div>
            {/* Filters */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Calendar size={18} style={{ color: 'var(--text-muted)' }} />
                        <select style={{
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-primary)',
                            borderRadius: 6,
                            padding: '8px 12px',
                            color: 'var(--text-primary)',
                            fontSize: '0.875rem'
                        }}>
                            <option>Today</option>
                            <option>Last 7 Days</option>
                            <option>Last 30 Days</option>
                        </select>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Filter size={18} style={{ color: 'var(--text-muted)' }} />
                        <select style={{
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-primary)',
                            borderRadius: 6,
                            padding: '8px 12px',
                            color: 'var(--text-primary)',
                            fontSize: '0.875rem'
                        }}>
                            <option>All Departments</option>
                            <option>IT</option>
                            <option>Finance</option>
                            <option>HR</option>
                            <option>R&D</option>
                        </select>
                    </div>

                    {/* Legend */}
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Risk Level:</span>
                        {[
                            { label: 'Low', color: 'rgba(34, 197, 94, 0.4)' },
                            { label: 'Medium', color: 'rgba(234, 179, 8, 0.7)' },
                            { label: 'High', color: 'rgba(249, 115, 22, 0.8)' },
                            { label: 'Critical', color: 'rgba(239, 68, 68, 0.9)' }
                        ].map(item => (
                            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{
                                    width: 12,
                                    height: 12,
                                    borderRadius: 2,
                                    background: item.color
                                }} />
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Heatmap */}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">User Activity Risk Heatmap</h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Click a cell to view details
                    </span>
                </div>

                <div style={{ overflowX: 'auto', position: 'relative' }}>
                    <div style={{ minWidth: 900 }} className="radar-container">
                        <div className="radar-scan"></div>

                        {/* Hour Headers */}
                        <div style={{ display: 'flex', marginBottom: 4 }}>
                            <div style={{ width: 120, flexShrink: 0 }} />
                            {hours.map(hour => (
                                <div
                                    key={hour}
                                    style={{
                                        width: 28,
                                        textAlign: 'center',
                                        fontSize: '0.65rem',
                                        color: 'var(--text-muted)',
                                        fontFamily: 'var(--font-mono)'
                                    }}
                                >
                                    {hour}
                                </div>
                            ))}
                        </div>

                        {/* Heatmap Rows */}
                        {heatmapData.map(row => (
                            <div key={row.user} style={{ display: 'flex', marginBottom: 2 }}>
                                <div style={{
                                    width: 120,
                                    flexShrink: 0,
                                    display: 'flex',
                                    alignItems: 'center',
                                    fontSize: '0.8rem',
                                    fontFamily: 'var(--font-mono)',
                                    color: 'var(--text-primary)'
                                }}>
                                    {row.user}
                                    <span style={{
                                        marginLeft: 8,
                                        fontSize: '0.65rem',
                                        color: 'var(--text-muted)'
                                    }}>
                                        {row.role}
                                    </span>
                                </div>
                                {row.data.map((cell, idx) => (
                                    <div
                                        key={idx}
                                        onClick={() => setSelectedCell({ user: row.user, ...cell, role: row.role })}
                                        className={cell.risk >= 80 ? 'risk-cell-critical' : ''}
                                        style={{
                                            width: 28,
                                            height: 24,
                                            background: getRiskColor(cell.risk),
                                            borderRadius: 2,
                                            margin: '0 1px',
                                            cursor: 'pointer',
                                            transition: 'transform 0.15s, box-shadow 0.15s',
                                            border: selectedCell?.user === row.user && selectedCell?.hour === cell.hour
                                                ? '2px solid var(--accent-primary)'
                                                : '1px solid transparent'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.transform = 'scale(1.2)'
                                            e.currentTarget.style.zIndex = '10'
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'scale(1)'
                                            e.currentTarget.style.zIndex = '1'
                                        }}
                                        title={`${row.user} at ${cell.hour}: Risk ${cell.risk}`}
                                    />
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div style={{ marginTop: 24 }}>
                <SystemTerminal />
            </div>

            {/* Selected Cell Details */}
            {selectedCell && (
                <div className="card" style={{ marginTop: 24 }}>
                    <div className="card-header">
                        <h3 className="card-title">Selected Activity Details</h3>
                        <button
                            onClick={() => setSelectedCell(null)}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--text-muted)',
                                cursor: 'pointer',
                                fontSize: '1.25rem'
                            }}
                        >
                            ×
                        </button>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>User</div>
                            <div className="mono" style={{ fontSize: '1.125rem', fontWeight: 600 }}>{selectedCell.user}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Time</div>
                            <div style={{ fontSize: '1.125rem' }}>{selectedCell.hour}:00</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Role</div>
                            <div style={{ fontSize: '1.125rem' }}>{selectedCell.role}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Risk Score</div>
                            <div style={{
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                color: selectedCell.risk >= 60 ? 'var(--risk-critical)' :
                                    selectedCell.risk >= 40 ? 'var(--risk-medium)' :
                                        'var(--risk-low)'
                            }}>
                                {selectedCell.risk}
                            </div>
                        </div>
                    </div>
                    <div style={{ marginTop: 16 }}>
                        <button className="btn btn-primary">
                            View Full Forensics
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default RiskHeatmap
