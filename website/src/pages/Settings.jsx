import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { Battery, Bell, Shield, Database, Trash2, Save } from 'lucide-react';

const SettingsSection = ({ title, children }) => (
    <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{
            fontSize: '1rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            marginBottom: 16,
            borderBottom: '1px solid var(--border-primary)',
            paddingBottom: 8
        }}>
            {title}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {children}
        </div>
    </div>
);

const ToggleSetting = ({ icon: Icon, title, description, checked, onChange }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{
                width: 40, height: 40,
                borderRadius: 8,
                background: 'var(--bg-tertiary)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'var(--accent-primary)'
            }}>
                <Icon size={20} />
            </div>
            <div>
                <div style={{ fontWeight: 500 }}>{title}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{description}</div>
            </div>
        </div>
        <label className="switch" style={{ position: 'relative', display: 'inline-block', width: 48, height: 24 }}>
            <input
                type="checkbox"
                checked={checked}
                onChange={onChange}
                style={{ opacity: 0, width: 0, height: 0 }}
            />
            <span style={{
                position: 'absolute',
                cursor: 'pointer',
                top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: checked ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                transition: '.4s',
                borderRadius: 24,
                border: '1px solid var(--border-primary)'
            }}>
                <span style={{
                    position: 'absolute',
                    content: '""',
                    height: 18, width: 18,
                    left: checked ? 26 : 3,
                    bottom: 2,
                    backgroundColor: 'white',
                    transition: '.4s',
                    borderRadius: '50%'
                }} />
            </span>
        </label>
    </div>
);

const Settings = () => {
    const { lowPowerMode, toggleLowPowerMode } = useTheme();

    return (
        <div className="settings-page">
            <h2 className="header-title" style={{ marginBottom: 24 }}>System Configuration</h2>

            <SettingsSection title="Performance & Visuals">
                <ToggleSetting
                    icon={Battery}
                    title="Stealth Mode (Low Power)"
                    description="Disable advanced animations (Matrix rain, 3D tilt) to save battery."
                    checked={lowPowerMode}
                    onChange={toggleLowPowerMode}
                />
            </SettingsSection>

            <SettingsSection title="Notifications">
                <ToggleSetting
                    icon={Bell}
                    title="Real-time Alerts"
                    description="Receive toast notifications for high-risk events."
                    checked={true}
                    onChange={() => { }}
                />
                <ToggleSetting
                    icon={Shield}
                    title="Email Reports"
                    description="Daily summary of security incidents sent to admin."
                    checked={false}
                    onChange={() => { }}
                />
            </SettingsSection>

            <SettingsSection title="System Data">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                        <div style={{
                            width: 40, height: 40,
                            borderRadius: 8,
                            background: 'rgba(239, 68, 68, 0.1)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'var(--risk-critical)'
                        }}>
                            <Trash2 size={20} />
                        </div>
                        <div>
                            <div style={{ fontWeight: 500 }}>Clear Cache</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Free up local storage space.</div>
                        </div>
                    </div>
                    <button className="btn btn-secondary" style={{ color: 'var(--risk-critical)', borderColor: 'var(--risk-critical)' }}>
                        Clear Now
                    </button>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                        <div style={{
                            width: 40, height: 40,
                            borderRadius: 8,
                            background: 'var(--bg-tertiary)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'var(--text-primary)'
                        }}>
                            <Database size={20} />
                        </div>
                        <div>
                            <div style={{ fontWeight: 500 }}>Export Logs</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Download system logs as JSON.</div>
                        </div>
                    </div>
                    <button className="btn btn-secondary">
                        <Save size={16} /> Export
                    </button>
                </div>
            </SettingsSection>
        </div>
    );
};

export default Settings;
