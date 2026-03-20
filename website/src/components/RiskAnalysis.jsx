import { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, CheckCircle, XCircle, Info } from 'lucide-react'

const API_BASE = '/api'

function RiskAnalysis({ userId, onClose }) {
    const [riskData, setRiskData] = useState(null)
    const [explanation, setExplanation] = useState(null)
    const [loading, setLoading] = useState(true)
    const [explanationLoading, setExplanationLoading] = useState(false)
    const [selectedDate, setSelectedDate] = useState(null)

    useEffect(() => {
        fetchRiskData()
    }, [userId])

    const fetchRiskData = async () => {
        try {
            setLoading(true)
            const response = await fetch(`${API_BASE}/analysis/user/${userId}`)
            if (!response.ok) throw new Error('Failed to fetch risk data')
            const data = await response.json()
            setRiskData(data)

            // Auto-select latest high risk date if any
            if (data.history && data.history.length > 0) {
                const highRiskDay = data.history.find(d => d.risk_score > 50) || data.history[data.history.length - 1]
                handleExplain(highRiskDay.date)
            }
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleExplain = async (date) => {
        setSelectedDate(date)
        try {
            setExplanationLoading(true)
            const response = await fetch(`${API_BASE}/analysis/explain/${userId}/${date}`)
            if (!response.ok) throw new Error('Failed to fetch explanation')
            const data = await response.json()
            setExplanation(data.explanation)
        } catch (err) {
            console.error(err)
        } finally {
            setExplanationLoading(false)
        }
    }

    const submitFeedback = async (isTruePositive) => {
        try {
            const response = await fetch(`${API_BASE}/analysis/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    date: selectedDate,
                    is_true_positive: isTruePositive,
                    comments: "User feedback via Dashboard"
                })
            })
            if (response.ok) {
                alert("Feedback submitted successfully!")
            }
        } catch (err) {
            console.error(err)
        }
    }

    if (loading) return (
        <div className="card" style={{ padding: 24, textAlign: 'center' }}>
            <div className="loading-spinner"></div>
            <p style={{ marginTop: 12, color: 'var(--text-muted)' }}>Loading analysis...</p>
        </div>
    )

    return (
        <div className="card" style={{
            width: '90vw',
            maxWidth: 900,
            maxHeight: '85vh',
            overflow: 'auto',
            padding: 24
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
                    <AlertTriangle size={20} style={{ color: 'var(--risk-high)' }} />
                    Risk Analysis: <span className="mono">{userId}</span>
                </h3>
                <button
                    onClick={onClose}
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        fontSize: '1.5rem'
                    }}
                >✕</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                {/* History List */}
                <div>
                    <h4 style={{ fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
                        Activity Timeline
                    </h4>
                    <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {riskData?.history?.map((entry) => (
                            <div
                                key={entry.date}
                                onClick={() => handleExplain(entry.date)}
                                style={{
                                    padding: '8px 12px',
                                    borderRadius: 6,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    background: selectedDate === entry.date
                                        ? 'rgba(255,255,255,0.1)'
                                        : 'transparent',
                                    transition: 'background 0.2s'
                                }}
                                onMouseEnter={e => {
                                    if (selectedDate !== entry.date)
                                        e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
                                }}
                                onMouseLeave={e => {
                                    if (selectedDate !== entry.date)
                                        e.currentTarget.style.background = 'transparent'
                                }}
                            >
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    <span style={{ fontSize: '0.875rem' }}>{entry.date}</span>
                                    {entry.ip && (
                                        <span className="mono" style={{
                                            fontSize: '0.7rem',
                                            color: 'var(--text-muted)',
                                            opacity: 0.8
                                        }}>
                                            IP: {entry.ip}
                                        </span>
                                    )}
                                </div>
                                <span className="mono" style={{
                                    fontSize: '0.875rem',
                                    fontWeight: 600,
                                    color: entry.risk_score > 50 ? 'var(--risk-critical)' : 'var(--risk-low)'
                                }}>
                                    Score: {entry.risk_score}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Explainability Section */}
                <div>
                    <h4 style={{ fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
                        Risk Drivers {selectedDate && `for ${selectedDate}`}
                    </h4>

                    {explanationLoading ? (
                        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Analyzing...</div>
                    ) : explanation ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {Object.entries(explanation).slice(0, 5).map(([feature, impact]) => (
                                <div key={feature}>
                                    <div style={{
                                        display: 'flex', justifyContent: 'space-between',
                                        fontSize: '0.8rem', marginBottom: 4
                                    }}>
                                        <span style={{ textTransform: 'capitalize' }}>
                                            {feature.replace(/_/g, ' ')}
                                        </span>
                                        <span style={{ color: 'var(--text-muted)' }}>
                                            {impact.toFixed(3)}
                                        </span>
                                    </div>
                                    <div style={{
                                        width: '100%',
                                        height: 8,
                                        background: 'var(--bg-tertiary)',
                                        borderRadius: 4,
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{
                                            height: '100%',
                                            width: `${Math.min(100, Math.abs(impact) * 20)}%`,
                                            background: impact > 0
                                                ? 'var(--risk-critical)'
                                                : 'var(--risk-low)',
                                            borderRadius: 4,
                                            transition: 'width 0.3s'
                                        }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Select a date to view details.
                        </div>
                    )}

                    {/* Feedback Actions */}
                    {selectedDate && (
                        <div style={{
                            marginTop: 24,
                            paddingTop: 16,
                            borderTop: '1px solid var(--border-primary)'
                        }}>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                                Is this flagged correctly?
                            </p>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button
                                    onClick={() => submitFeedback(true)}
                                    className="btn btn-secondary"
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 6,
                                        padding: '6px 14px',
                                        color: 'var(--risk-low)',
                                        borderColor: 'var(--risk-low)'
                                    }}
                                >
                                    <CheckCircle size={16} />
                                    Confirm Risk
                                </button>
                                <button
                                    onClick={() => submitFeedback(false)}
                                    className="btn btn-secondary"
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 6,
                                        padding: '6px 14px',
                                        color: 'var(--risk-critical)',
                                        borderColor: 'var(--risk-critical)'
                                    }}
                                >
                                    <XCircle size={16} />
                                    Dismiss (False Positive)
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default RiskAnalysis
