import { useState, useEffect, useRef, useCallback } from 'react'
import {
    Mouse, Play, Square, Users, Activity, Shield, AlertTriangle,
    Eye, Crosshair, Zap, Clock, BarChart3, Target,
    ChevronDown, ChevronRight, Gauge, Fingerprint, MonitorDot
} from 'lucide-react'

// ─── Constants ──────────────────────────────────────────────────────────────

const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/mouse'

const RISK_COLORS = {
    low: '#00ff88',
    medium: '#ffbb33',
    high: '#ff3366',
    critical: '#ff0040',
}

const RISK_BG = {
    low: 'rgba(0,255,136,0.08)',
    medium: 'rgba(255,187,51,0.08)',
    high: 'rgba(255,51,102,0.08)',
    critical: 'rgba(255,0,64,0.08)',
}

// ─── Utility Components ─────────────────────────────────────────────────────

function AnimatedNumber({ value, decimals = 0, suffix = '' }) {
    const [display, setDisplay] = useState(0)
    const ref = useRef(null)
    useEffect(() => {
        const start = display
        const diff = value - start
        const duration = 600
        const startTime = performance.now()
        function animate(now) {
            const elapsed = now - startTime
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setDisplay(start + diff * eased)
            if (progress < 1) ref.current = requestAnimationFrame(animate)
        }
        ref.current = requestAnimationFrame(animate)
        return () => cancelAnimationFrame(ref.current)
    }, [value])
    return <span>{display.toFixed(decimals)}{suffix}</span>
}

function RiskBadge({ level }) {
    return (
        <span className="mt-risk-badge" style={{
            color: RISK_COLORS[level] || '#888',
            background: RISK_BG[level] || 'rgba(136,136,136,0.1)',
            border: `1px solid ${RISK_COLORS[level] || '#888'}33`,
        }}>
            {level.toUpperCase()}
        </span>
    )
}

function AnomalyGauge({ score, size = 120 }) {
    const radius = (size - 16) / 2
    const circumference = 2 * Math.PI * radius
    const offset = circumference - (score / 100) * circumference
    const color = score < 30 ? '#00ff88' : score < 60 ? '#ffbb33' : '#ff3366'

    return (
        <div className="mt-anomaly-gauge" style={{ width: size, height: size }}>
            <svg width={size} height={size}>
                <circle cx={size/2} cy={size/2} r={radius}
                    fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                <circle cx={size/2} cy={size/2} r={radius}
                    fill="none" stroke={color} strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', transition: 'stroke-dashoffset 1s ease' }}
                />
            </svg>
            <div className="mt-gauge-value" style={{ color }}>
                {Math.round(score)}
            </div>
            <div className="mt-gauge-label">ANOMALY</div>
        </div>
    )
}

// ─── Heatmap Visualization ──────────────────────────────────────────────────

function HeatmapGrid({ grid, maxValue }) {
    if (!grid || !grid.length) return <div className="mt-no-data">No heatmap data</div>

    return (
        <div className="mt-heatmap-grid">
            {grid.map((row, y) =>
                row.map((val, x) => {
                    const intensity = maxValue > 0 ? val / maxValue : 0
                    const r = Math.round(intensity * 255)
                    const g = Math.round((1 - intensity) * 100)
                    const b = Math.round(intensity * 100)
                    return (
                        <div key={`${x}-${y}`}
                            className="mt-heatmap-cell"
                            style={{
                                background: intensity > 0
                                    ? `rgba(${r}, ${g}, ${b}, ${0.1 + intensity * 0.9})`
                                    : 'rgba(255,255,255,0.02)',
                            }}
                            title={`(${x},${y}): ${val} events`}
                        />
                    )
                })
            )}
        </div>
    )
}

// ─── Live Trail Canvas ──────────────────────────────────────────────────────

function LiveTrailCanvas({ events, isTracking }) {
    const canvasRef = useRef(null)
    const animRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * 2
        canvas.height = rect.height * 2
        ctx.scale(2, 2)

        function draw() {
            ctx.clearRect(0, 0, rect.width, rect.height)

            // Draw grid
            ctx.strokeStyle = 'rgba(0, 212, 255, 0.04)'
            ctx.lineWidth = 0.5
            for (let x = 0; x < rect.width; x += 40) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, rect.height); ctx.stroke()
            }
            for (let y = 0; y < rect.height; y += 40) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(rect.width, y); ctx.stroke()
            }

            if (events.length < 2) {
                animRef.current = requestAnimationFrame(draw)
                return
            }

            // Scale coordinates to canvas
            const scaleX = rect.width / 1920
            const scaleY = rect.height / 1080

            // Draw trail
            const trail = events.slice(-300)
            for (let i = 1; i < trail.length; i++) {
                const prev = trail[i - 1]
                const curr = trail[i]
                const alpha = (i / trail.length) * 0.8 + 0.1
                const isClick = curr.event_type === 'click'

                ctx.beginPath()
                ctx.moveTo(prev.x * scaleX, prev.y * scaleY)
                ctx.lineTo(curr.x * scaleX, curr.y * scaleY)
                ctx.strokeStyle = isClick
                    ? `rgba(255, 51, 102, ${alpha})`
                    : `rgba(0, 212, 255, ${alpha})`
                ctx.lineWidth = isClick ? 3 : 1.5
                ctx.stroke()

                if (isClick) {
                    ctx.beginPath()
                    ctx.arc(curr.x * scaleX, curr.y * scaleY, 6, 0, Math.PI * 2)
                    ctx.fillStyle = `rgba(255, 51, 102, ${alpha * 0.6})`
                    ctx.fill()
                    ctx.strokeStyle = `rgba(255, 51, 102, ${alpha})`
                    ctx.lineWidth = 1.5
                    ctx.stroke()
                }
            }

            // Draw current position
            const last = trail[trail.length - 1]
            if (last && isTracking) {
                ctx.beginPath()
                ctx.arc(last.x * scaleX, last.y * scaleY, 4, 0, Math.PI * 2)
                ctx.fillStyle = '#00ff88'
                ctx.fill()
                // Pulse ring
                const pulse = (Date.now() % 1500) / 1500
                ctx.beginPath()
                ctx.arc(last.x * scaleX, last.y * scaleY, 4 + pulse * 16, 0, Math.PI * 2)
                ctx.strokeStyle = `rgba(0, 255, 136, ${1 - pulse})`
                ctx.lineWidth = 1.5
                ctx.stroke()
            }

            animRef.current = requestAnimationFrame(draw)
        }

        draw()
        return () => cancelAnimationFrame(animRef.current)
    }, [events, isTracking])

    return <canvas ref={canvasRef} className="mt-trail-canvas" />
}

// ─── Velocity Chart (mini sparkline) ────────────────────────────────────────

function VelocitySparkline({ velocities }) {
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas || velocities.length < 2) return
        const ctx = canvas.getContext('2d')
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * 2
        canvas.height = rect.height * 2
        ctx.scale(2, 2)

        ctx.clearRect(0, 0, rect.width, rect.height)

        const data = velocities.slice(-100)
        const max = Math.max(...data, 0.001)
        const step = rect.width / (data.length - 1)

        // Fill gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, rect.height)
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)')
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)')

        ctx.beginPath()
        ctx.moveTo(0, rect.height)
        data.forEach((v, i) => {
            ctx.lineTo(i * step, rect.height - (v / max) * rect.height * 0.9)
        })
        ctx.lineTo(rect.width, rect.height)
        ctx.fillStyle = gradient
        ctx.fill()

        // Line
        ctx.beginPath()
        data.forEach((v, i) => {
            const x = i * step
            const y = rect.height - (v / max) * rect.height * 0.9
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        })
        ctx.strokeStyle = '#00d4ff'
        ctx.lineWidth = 1.5
        ctx.stroke()
    }, [velocities])

    return <canvas ref={canvasRef} className="mt-sparkline" />
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function MouseTracking() {
    const [employees, setEmployees] = useState([])
    const [selectedEmployee, setSelectedEmployee] = useState(null)
    const [isTracking, setIsTracking] = useState(false)
    const [sessionId, setSessionId] = useState(null)
    const [metrics, setMetrics] = useState(null)
    const [heatmapData, setHeatmapData] = useState(null)
    const [trailEvents, setTrailEvents] = useState([])
    const [velocities, setVelocities] = useState([])
    const [anomalyScore, setAnomalyScore] = useState(0)
    const [eventCount, setEventCount] = useState(0)
    const [liveStats, setLiveStats] = useState({
        distance: 0, clicks: 0, avgVelocity: 0, idlePct: 0
    })
    const [expandedSection, setExpandedSection] = useState('overview')
    const [statusMsg, setStatusMsg] = useState('')

    // Refs for tracking loop
    const trackingRef = useRef(false)
    const eventBufferRef = useRef([])
    const lastEventRef = useRef(null)
    const prevVelocityRef = useRef(0)
    const sessionIdRef = useRef(null)

    // Load employees on mount
    useEffect(() => {
        fetch(`${API_BASE}/demo/employees`)
            .then(r => r.json())
            .then(data => {
                setEmployees(data.employees || [])
                if (data.employees?.length > 0) {
                    setSelectedEmployee(data.employees[0])
                }
            })
            .catch(() => setStatusMsg('Failed to load employees'))
    }, [])

    // Mouse event handler (captures real mouse movement)
    const handleMouseMove = useCallback((e) => {
        if (!trackingRef.current) return

        const now = performance.now() + performance.timeOrigin
        const prev = lastEventRef.current

        const evt = {
            x: e.clientX,
            y: e.clientY,
            timestamp: now,
            event_type: 'move',
            button: null,
            scroll_delta: null,
        }

        // Calculate velocity for live display
        if (prev) {
            const dx = evt.x - prev.x
            const dy = evt.y - prev.y
            const dt = Math.max(now - prev.timestamp, 1)
            const velocity = Math.sqrt(dx * dx + dy * dy) / dt
            prevVelocityRef.current = velocity
            setVelocities(v => [...v.slice(-200), velocity])
        }

        lastEventRef.current = evt
        eventBufferRef.current.push(evt)
        setTrailEvents(events => [...events.slice(-500), evt])
    }, [])

    const handleClick = useCallback((e) => {
        if (!trackingRef.current) return
        const now = performance.now() + performance.timeOrigin
        const evt = {
            x: e.clientX, y: e.clientY,
            timestamp: now, event_type: 'click',
            button: e.button, scroll_delta: null,
        }
        eventBufferRef.current.push(evt)
        setTrailEvents(events => [...events.slice(-500), evt])
    }, [])

    const handleScroll = useCallback((e) => {
        if (!trackingRef.current) return
        const now = performance.now() + performance.timeOrigin
        const evt = {
            x: e.clientX || 0, y: e.clientY || 0,
            timestamp: now, event_type: 'scroll',
            button: null, scroll_delta: e.deltaY,
        }
        eventBufferRef.current.push(evt)
    }, [])

    // Start tracking
    const startTracking = async () => {
        if (!selectedEmployee) return

        try {
            const res = await fetch(`${API_BASE}/session/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: selectedEmployee.user_id,
                    pc_id: selectedEmployee.pc_id || 'WS-DEMO-001',
                    application: 'UBA Dashboard Demo',
                    screen_width: window.innerWidth,
                    screen_height: window.innerHeight,
                }),
            })
            const data = await res.json()
            setSessionId(data.session_id)
            sessionIdRef.current = data.session_id
            setIsTracking(true)
            trackingRef.current = true
            setTrailEvents([])
            setVelocities([])
            setAnomalyScore(0)
            setEventCount(0)
            setLiveStats({ distance: 0, clicks: 0, avgVelocity: 0, idlePct: 0 })
            setStatusMsg(`Session ${data.session_id} started`)

            // Add global listeners
            document.addEventListener('mousemove', handleMouseMove)
            document.addEventListener('click', handleClick)
            document.addEventListener('wheel', handleScroll)
        } catch (err) {
            setStatusMsg(`Error: ${err.message}`)
        }
    }

    // Stop tracking
    const stopTracking = async () => {
        trackingRef.current = false
        setIsTracking(false)

        // Remove global listeners
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('click', handleClick)
        document.removeEventListener('wheel', handleScroll)

        // Flush remaining events
        if (eventBufferRef.current.length > 0 && sessionIdRef.current) {
            await flushEvents()
        }

        // End session
        if (sessionIdRef.current) {
            try {
                const res = await fetch(`${API_BASE}/session/end`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionIdRef.current,
                        user_id: selectedEmployee.user_id,
                    }),
                })
                const data = await res.json()
                setMetrics(data.final_metrics)
                setAnomalyScore(data.anomaly_scores?.overall || 0)
                setStatusMsg(`Session ended — anomaly score: ${Math.round(data.anomaly_scores?.overall || 0)}`)
            } catch (err) {
                setStatusMsg(`Error ending session: ${err.message}`)
            }

            // Load heatmap
            try {
                const hRes = await fetch(`${API_BASE}/heatmap/${sessionIdRef.current}`)
                const hData = await hRes.json()
                setHeatmapData(hData)
            } catch {}
        }
    }

    // Flush event buffer to backend
    const flushEvents = async () => {
        const events = [...eventBufferRef.current]
        eventBufferRef.current = []
        if (events.length === 0 || !sessionIdRef.current) return

        try {
            const res = await fetch(`${API_BASE}/events`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: selectedEmployee.user_id,
                    session_id: sessionIdRef.current,
                    events: events,
                    screen_width: window.innerWidth,
                    screen_height: window.innerHeight,
                }),
            })
            const data = await res.json()
            setEventCount(data.total_events || 0)
            setAnomalyScore(data.current_anomaly || 0)
        } catch {}
    }

    // Periodic flush + metrics poll
    useEffect(() => {
        if (!isTracking) return
        const interval = setInterval(async () => {
            await flushEvents()
            // Poll live metrics
            if (sessionIdRef.current) {
                try {
                    const res = await fetch(`${API_BASE}/session/${sessionIdRef.current}`)
                    const data = await res.json()
                    setMetrics(data)
                    setLiveStats({
                        distance: data.total_distance_px || 0,
                        clicks: data.total_clicks || 0,
                        avgVelocity: data.avg_velocity_px_ms || 0,
                        idlePct: data.idle_percentage || 0,
                    })
                    setAnomalyScore(data.anomaly_scores?.overall || 0)
                } catch {}
            }
        }, 1000)
        return () => clearInterval(interval)
    }, [isTracking])

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('click', handleClick)
            document.removeEventListener('wheel', handleScroll)
        }
    }, [])

    const toggleSection = (s) => setExpandedSection(expandedSection === s ? null : s)

    return (
        <div className="mt-container">
            {/* ── Top Bar ─────────────────────────────────────────── */}
            <div className="mt-topbar">
                <div className="mt-topbar-left">
                    <Fingerprint size={20} style={{ color: '#00d4ff' }} />
                    <span className="mt-topbar-title">Mouse Biometric Tracking</span>
                    {isTracking && (
                        <span className="mt-live-dot">
                            <span className="mt-live-dot-inner" />
                            LIVE
                        </span>
                    )}
                </div>
                <div className="mt-topbar-right">
                    <div className="mt-topbar-stat">
                        <Activity size={14} />
                        <span><AnimatedNumber value={eventCount} /> events</span>
                    </div>
                    <div className="mt-topbar-stat">
                        <Zap size={14} />
                        <span><AnimatedNumber value={liveStats.avgVelocity} decimals={2} /> px/ms</span>
                    </div>
                </div>
            </div>

            <div className="mt-layout">
                {/* ── Left Panel: Employee Selector ─────────────────── */}
                <div className="mt-sidebar">
                    <div className="mt-sidebar-header">
                        <Users size={16} />
                        <span>Employees</span>
                    </div>
                    <div className="mt-employee-list">
                        {employees.map(emp => (
                            <button
                                key={emp.user_id}
                                className={`mt-employee-card ${selectedEmployee?.user_id === emp.user_id ? 'selected' : ''}`}
                                onClick={() => {
                                    if (!isTracking) setSelectedEmployee(emp)
                                }}
                                disabled={isTracking}
                            >
                                <div className="mt-emp-avatar" style={{
                                    background: `linear-gradient(135deg, ${emp.avatar_color}, ${emp.avatar_color}66)`,
                                }}>
                                    {emp.name.split(' ').map(n => n[0]).join('')}
                                </div>
                                <div className="mt-emp-info">
                                    <div className="mt-emp-name">{emp.name}</div>
                                    <div className="mt-emp-role">{emp.role}</div>
                                    <div className="mt-emp-dept">{emp.department}</div>
                                </div>
                                <div className="mt-emp-status">
                                    <RiskBadge level={emp.risk_level} />
                                    {emp.has_active_session && (
                                        <span className="mt-emp-tracking">
                                            <Eye size={10} /> TRACKING
                                        </span>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* ── Center Panel: Live Visualization ──────────────── */}
                <div className="mt-center">
                    {/* Control Bar */}
                    <div className="mt-control-bar">
                        <div className="mt-selected-info">
                            {selectedEmployee && (
                                <>
                                    <div className="mt-sel-avatar" style={{
                                        background: `linear-gradient(135deg, ${selectedEmployee.avatar_color}, ${selectedEmployee.avatar_color}66)`,
                                    }}>
                                        {selectedEmployee.name.split(' ').map(n => n[0]).join('')}
                                    </div>
                                    <div>
                                        <div className="mt-sel-name">{selectedEmployee.name}</div>
                                        <div className="mt-sel-detail">
                                            {selectedEmployee.pc_id} · {selectedEmployee.department}
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                        <div className="mt-control-actions">
                            {!isTracking ? (
                                <button className="mt-btn mt-btn-start" onClick={startTracking}
                                    disabled={!selectedEmployee}>
                                    <Play size={16} />
                                    Start Tracking
                                </button>
                            ) : (
                                <button className="mt-btn mt-btn-stop" onClick={stopTracking}>
                                    <Square size={16} />
                                    Stop Tracking
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Live Trail */}
                    <div className="mt-trail-container">
                        <div className="mt-trail-header">
                            <Crosshair size={14} />
                            <span>Live Mouse Trail</span>
                            {isTracking && <span className="mt-trail-hint">Move your mouse anywhere on the page</span>}
                        </div>
                        <LiveTrailCanvas events={trailEvents} isTracking={isTracking} />
                        {!isTracking && trailEvents.length === 0 && (
                            <div className="mt-trail-placeholder">
                                <Mouse size={48} strokeWidth={1} />
                                <p>Click "Start Tracking" to begin capturing mouse biometrics</p>
                                <p className="mt-trail-sub">Real-time movement analysis &amp; anomaly detection</p>
                            </div>
                        )}
                    </div>

                    {/* Velocity Sparkline */}
                    {(isTracking || velocities.length > 0) && (
                        <div className="mt-sparkline-container">
                            <div className="mt-sparkline-header">
                                <Activity size={14} />
                                <span>Velocity Profile</span>
                            </div>
                            <VelocitySparkline velocities={velocities} />
                        </div>
                    )}

                    {/* Heatmap (after session ends) */}
                    {heatmapData && !isTracking && (
                        <div className="mt-section">
                            <div className="mt-section-header" onClick={() => toggleSection('heatmap')}>
                                <Target size={14} />
                                <span>Movement Heatmap</span>
                                {expandedSection === 'heatmap' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </div>
                            {expandedSection === 'heatmap' && (
                                <HeatmapGrid grid={heatmapData.grid} maxValue={heatmapData.max_value} />
                            )}
                        </div>
                    )}

                    {/* Status */}
                    {statusMsg && (
                        <div className="mt-status">{statusMsg}</div>
                    )}
                </div>

                {/* ── Right Panel: Metrics ──────────────────────────── */}
                <div className="mt-metrics-panel">
                    {/* Anomaly Gauge */}
                    <div className="mt-gauge-container">
                        <AnomalyGauge score={anomalyScore} size={140} />
                    </div>

                    {/* Quick Stats */}
                    <div className="mt-quick-stats">
                        <div className="mt-stat-card">
                            <div className="mt-stat-icon"><MonitorDot size={16} /></div>
                            <div className="mt-stat-value">
                                <AnimatedNumber value={liveStats.distance} decimals={0} />
                            </div>
                            <div className="mt-stat-label">Distance (px)</div>
                        </div>
                        <div className="mt-stat-card">
                            <div className="mt-stat-icon"><Mouse size={16} /></div>
                            <div className="mt-stat-value">
                                <AnimatedNumber value={liveStats.clicks} />
                            </div>
                            <div className="mt-stat-label">Clicks</div>
                        </div>
                        <div className="mt-stat-card">
                            <div className="mt-stat-icon"><Gauge size={16} /></div>
                            <div className="mt-stat-value">
                                <AnimatedNumber value={liveStats.avgVelocity} decimals={3} />
                            </div>
                            <div className="mt-stat-label">Avg Velocity</div>
                        </div>
                        <div className="mt-stat-card">
                            <div className="mt-stat-icon"><Clock size={16} /></div>
                            <div className="mt-stat-value">
                                <AnimatedNumber value={liveStats.idlePct} decimals={1} suffix="%" />
                            </div>
                            <div className="mt-stat-label">Idle Time</div>
                        </div>
                    </div>

                    {/* Detailed Metrics (collapsible) */}
                    {metrics && (
                        <>
                            <div className="mt-section">
                                <div className="mt-section-header" onClick={() => toggleSection('physics')}>
                                    <Zap size={14} />
                                    <span>Physics Metrics</span>
                                    {expandedSection === 'physics' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                </div>
                                {expandedSection === 'physics' && (
                                    <div className="mt-detail-grid">
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Max Velocity</span>
                                            <span className="mt-detail-val">{metrics.max_velocity_px_ms?.toFixed(4)} px/ms</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Velocity StdDev</span>
                                            <span className="mt-detail-val">{metrics.velocity_std?.toFixed(4)}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Avg Acceleration</span>
                                            <span className="mt-detail-val">{metrics.avg_acceleration?.toFixed(6)}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Avg Jerk</span>
                                            <span className="mt-detail-val">{metrics.avg_jerk?.toFixed(8)}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Jerk Spikes</span>
                                            <span className="mt-detail-val">{metrics.jerk_spikes}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Avg Curvature</span>
                                            <span className="mt-detail-val">{metrics.avg_curvature?.toFixed(6)}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Straightness Index</span>
                                            <span className="mt-detail-val">{metrics.straightness_index?.toFixed(4)}</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="mt-section">
                                <div className="mt-section-header" onClick={() => toggleSection('interaction')}>
                                    <BarChart3 size={14} />
                                    <span>Interaction Metrics</span>
                                    {expandedSection === 'interaction' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                </div>
                                {expandedSection === 'interaction' && (
                                    <div className="mt-detail-grid">
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Left Clicks</span>
                                            <span className="mt-detail-val">{metrics.left_clicks}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Right Clicks</span>
                                            <span className="mt-detail-val">{metrics.right_clicks}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Double Clicks</span>
                                            <span className="mt-detail-val">{metrics.double_clicks}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Click Rate</span>
                                            <span className="mt-detail-val">{metrics.click_rate_per_min?.toFixed(2)}/min</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Scroll Events</span>
                                            <span className="mt-detail-val">{metrics.scroll_events}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Drag Events</span>
                                            <span className="mt-detail-val">{metrics.drag_events}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Pause Count</span>
                                            <span className="mt-detail-val">{metrics.pause_count}</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Avg Pause</span>
                                            <span className="mt-detail-val">{metrics.avg_pause_ms?.toFixed(0)} ms</span>
                                        </div>
                                        <div className="mt-detail-row">
                                            <span className="mt-detail-key">Duration</span>
                                            <span className="mt-detail-val">{metrics.duration_readable}</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="mt-section">
                                <div className="mt-section-header" onClick={() => toggleSection('anomaly')}>
                                    <AlertTriangle size={14} />
                                    <span>Anomaly Breakdown</span>
                                    {expandedSection === 'anomaly' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                </div>
                                {expandedSection === 'anomaly' && metrics.anomaly_scores && (
                                    <div className="mt-anomaly-breakdown">
                                        {Object.entries(metrics.anomaly_scores).filter(([k]) => k !== 'overall').map(([key, val]) => (
                                            <div className="mt-anomaly-bar-row" key={key}>
                                                <span className="mt-anomaly-bar-label">
                                                    {key.replace(/_/g, ' ')}
                                                </span>
                                                <div className="mt-anomaly-bar-track">
                                                    <div className="mt-anomaly-bar-fill"
                                                        style={{
                                                            width: `${Math.min(val / 25 * 100, 100)}%`,
                                                            background: val < 8 ? '#00ff88' : val < 16 ? '#ffbb33' : '#ff3366',
                                                        }}
                                                    />
                                                </div>
                                                <span className="mt-anomaly-bar-val">{val.toFixed(1)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
