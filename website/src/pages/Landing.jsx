import { Link } from 'react-router-dom'
import { Shield, Activity, Lock, Eye, ArrowRight, CheckCircle } from 'lucide-react'

function Landing() {
    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* Hero Section */}
            <div style={{
                textAlign: 'center',
                padding: '80px 20px',
                background: 'linear-gradient(180deg, rgba(6, 182, 212, 0.1) 0%, transparent 100%)',
                borderRadius: 24,
                marginBottom: 60,
                border: '1px solid var(--border-primary)'
            }}>
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'rgba(6, 182, 212, 0.15)',
                    padding: '8px 16px',
                    borderRadius: 30,
                    color: 'var(--accent-primary)',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    marginBottom: 24
                }}>
                    <Shield size={16} />
                    <span>UEBA & Insider Threat Detection System</span>
                </div>

                <h1 style={{
                    fontSize: '3.5rem',
                    fontWeight: 700,
                    marginBottom: 24,
                    lineHeight: 1.1,
                    background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                }}>
                    Detect Threats Before<br />They Become Breaches
                </h1>

                <p style={{
                    fontSize: '1.25rem',
                    color: 'var(--text-secondary)',
                    maxWidth: 700,
                    margin: '0 auto 40px',
                    lineHeight: 1.6
                }}>
                    Advanced User Behavior Analytics powered by LSTM Autoencoders and Isolation Forests.
                    Real-time anomaly detection, risk scoring, and forensic timeline analysis.
                </p>

                <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
                    <Link to="/" className="btn btn-primary" style={{ padding: '12px 32px', fontSize: '1rem' }}>
                        Launch Live Dashboard
                        <ArrowRight size={18} />
                    </Link>
                    <a href="https://github.com/your-repo" target="_blank" className="btn btn-secondary" style={{ padding: '12px 32px', fontSize: '1rem' }}>
                        View Documentation
                    </a>
                </div>
            </div>

            {/* Features Grid */}
            <div className="grid-3" style={{ marginBottom: 80 }}>
                {[
                    {
                        icon: <Activity />,
                        title: 'Behavioral Analytics',
                        desc: 'Detects anomalies in user actions using baseline models (Isolation Forest) and deep learning (LSTM).'
                    },
                    {
                        icon: <Lock />,
                        title: 'Risk Scoring Engine',
                        desc: 'Context-aware risk scoring that weights activities based on user role, time of day, and asset sensitivity.'
                    },
                    {
                        icon: <Eye />,
                        title: 'Forensic Timeline',
                        desc: 'Detailed reconstruction of user sessions to investigate potential insider threats and policy violations.'
                    }
                ].map((feature, idx) => (
                    <div key={idx} className="card" style={{ padding: 32 }}>
                        <div style={{
                            width: 48,
                            height: 48,
                            borderRadius: 12,
                            background: 'rgba(6, 182, 212, 0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--accent-primary)',
                            marginBottom: 20
                        }}>
                            {feature.icon}
                        </div>
                        <h3 style={{ fontSize: '1.25rem', marginBottom: 12 }}>{feature.title}</h3>
                        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{feature.desc}</p>
                    </div>
                ))}
            </div>

            {/* Technical Stack */}
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
                <h2 style={{ marginBottom: 40 }}>System Architecture</h2>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: 32
                }}>
                    {[
                        { title: 'Data Pipeline', items: ['Normalization', 'Schema Validation', 'Sequence Creation'] },
                        { title: 'Machine Learning', items: ['LSTM Autoencoder', 'Isolation Forest', 'One-Class SVM'] },
                        { title: 'Security', items: ['PII Masking', 'RBAC', 'Audit Logging'] },
                        { title: 'Frontend', items: ['React + Vite', 'Recharts', 'FastAPI Backend'] }
                    ].map((stack, idx) => (
                        <div key={idx} style={{ textAlign: 'left' }}>
                            <h4 style={{
                                color: 'var(--accent-primary)',
                                marginBottom: 16,
                                textTransform: 'uppercase',
                                fontSize: '0.875rem',
                                letterSpacing: '0.05em'
                            }}>
                                {stack.title}
                            </h4>
                            <ul style={{ listStyle: 'none' }}>
                                {stack.items.map((item, i) => (
                                    <li key={i} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 8,
                                        marginBottom: 10,
                                        color: 'var(--text-secondary)'
                                    }}>
                                        <CheckCircle size={14} style={{ color: 'var(--risk-low)' }} />
                                        {item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

export default Landing
