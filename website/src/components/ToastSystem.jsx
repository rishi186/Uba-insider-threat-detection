import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, BadgeAlert } from 'lucide-react';

const ToastSystem = () => {
    const [toasts, setToasts] = useState([]);

    const addToast = (type, title, message) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, type, title, message }]);
        setTimeout(() => removeToast(id), 5000);
    };

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    // Simulated Random Breaches
    useEffect(() => {
        const timer = setInterval(() => {
            if (Math.random() > 0.7) { // 30% chance every check
                const threats = [
                    { title: 'Suspicious IP', msg: 'Connection attempt from Blocked Region (CN)' },
                    { title: 'Privilege Esc.', msg: 'User ADMIN_01 modified system root' },
                    { title: 'Data Exfil', msg: 'Large outbound transfer detected (2GB)' },
                    { title: 'Brute Force', msg: '15 failed login attempts on SSH' }
                ];
                const threat = threats[Math.floor(Math.random() * threats.length)];
                addToast('critical', threat.title, threat.msg);
            }
        }, 8000); // Check every 8 seconds

        return () => clearInterval(timer);
    }, []);

    return (
        <div className="toast-container">
            {toasts.map(toast => (
                <div key={toast.id} className={`toast ${toast.type}`}>
                    <div className="toast-icon">
                        <AlertTriangle color={toast.type === 'critical' ? '#ef4444' : '#06b6d4'} />
                    </div>
                    <div>
                        <div className="toast-title" style={{ color: toast.type === 'critical' ? '#ef4444' : '#06b6d4' }}>
                            {toast.title}
                        </div>
                        <div className="toast-message">{toast.message}</div>
                    </div>
                    {/* Progress bar could go here */}
                </div>
            ))}
        </div>
    );
};

export default ToastSystem;
