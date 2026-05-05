import React from 'react';
import { useRole } from '../context/RoleContext';

const RoleGuard = ({ allowedRoles, children }) => {
    const { role } = useRole();

    if (allowedRoles && !allowedRoles.includes(role)) {
        return (
            <div className="card scan-effect" style={{ textAlign: 'center', padding: '60px', marginTop: '20px' }}>
                <div className="scan-container">
                    <div className="scanner-line"></div>
                    <h2 style={{ color: 'var(--risk-critical)', margin: '0 0 10px 0' }}>ACCESS DENIED</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>
                        Your current authorization level [{role.toUpperCase()}] is insufficient to view this highly classified module.
                    </p>
                </div>
            </div>
        );
    }

    return <>{children}</>;
};

export default RoleGuard;
