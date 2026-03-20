import React, { useState, useEffect, useRef } from 'react';

const LOG_TYPES = ['INFO', 'WARN', 'CRIT', 'NET', 'AUTH'];
const ACTIONS = [
    'Scanning ports...',
    'Packet handshake established',
    'User U1024 analyzing file',
    'Encrypted tunnel active',
    'Anomaly score calculation: 0.02',
    'Updating risk vectors',
    'Database connection pool: OK',
    'Forensic timeline updated',
    'Signal interception: Negative'
];

const SystemTerminal = () => {
    const [logs, setLogs] = useState([]);
    const bottomRef = useRef(null);

    useEffect(() => {
        const addLog = () => {
            const type = LOG_TYPES[Math.floor(Math.random() * LOG_TYPES.length)];
            const action = ACTIONS[Math.floor(Math.random() * ACTIONS.length)];
            const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
            const id = Math.random().toString(36).substr(2, 9);

            const newLog = { id, timestamp, type, action };

            setLogs(prev => {
                const updated = [...prev, newLog];
                if (updated.length > 20) updated.shift(); // Keep last 20
                return updated;
            });
        };

        const interval = setInterval(addLog, 800); // New log every 800ms
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="card terminal-card" style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            height: '200px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: '#050a14',
            border: '1px solid var(--border-primary)'
        }}>
            <div style={{
                padding: '8px 12px',
                borderBottom: '1px solid var(--border-primary)',
                background: 'rgba(255,255,255,0.05)',
                display: 'flex',
                justifyContent: 'space-between',
                color: 'var(--text-muted)'
            }}>
                <span>SYSTEM_LOGS.EXE</span>
                <span className="live-indicator">RUNNING</span>
            </div>
            <div style={{ padding: '12px', overflowY: 'auto', flex: 1 }} className="no-scrollbar">
                {logs.map(log => (
                    <div key={log.id} style={{ marginBottom: 4, display: 'flex', gap: 8 }}>
                        <span style={{ color: 'var(--text-muted)' }}>[{log.timestamp}]</span>
                        <span style={{
                            color: log.type === 'CRIT' ? 'var(--risk-critical)' :
                                log.type === 'WARN' ? 'var(--risk-high)' :
                                    'var(--accent-primary)',
                            fontWeight: 600,
                            minWidth: '40px'
                        }}>{log.type}</span>
                        <span style={{ color: 'var(--text-primary)' }}>{log.action}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default SystemTerminal;
