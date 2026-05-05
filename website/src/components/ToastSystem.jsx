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

    useEffect(() => {
        const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws') + '/api/ws/streams';
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => console.log('ToastSystem: Connected to UBA WebSockets');
        
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'new_alert') {
                    const data = msg.data;
                    addToast(
                        data.severity === 'critical' ? 'critical' : 'warning',
                        data.type || 'System Alert',
                        `${data.user_id}: ${data.message}`
                    );
                }
            } catch (err) {
                console.error('WebSocket message parse error:', err);
            }
        };

        ws.onclose = () => console.log('ToastSystem: WebSocket disconnected');

        return () => {
            ws.close();
        };
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
