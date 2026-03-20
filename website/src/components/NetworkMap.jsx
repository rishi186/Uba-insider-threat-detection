import React, { useState } from 'react';
import { User, FileText, Globe, Server, Smartphone, Laptop } from 'lucide-react';

const NetworkMap = () => {
    // Simple star topology
    const center = { x: 300, y: 200, label: 'User U1024' };
    const nodes = [
        { id: 1, x: 100, y: 80, type: 'file', label: 'project_alpha.pdf' },
        { id: 2, x: 500, y: 80, type: 'web', label: '192.168.1.45' },
        { id: 3, x: 500, y: 320, type: 'server', label: 'DB-Main-01' },
        { id: 4, x: 100, y: 320, type: 'device', label: 'USB-Disk-X' },
        { id: 5, x: 300, y: 60, type: 'device', label: 'Workstation' }
    ];

    const [activeNode, setActiveNode] = useState(null);

    return (
        <div className="card" style={{ height: '450px', position: 'relative', overflow: 'hidden', padding: 0 }}>
            <div className="card-header" style={{ position: 'absolute', top: 20, left: 20, zIndex: 10 }}>
                <h3 className="card-title">Activity Network Graph</h3>
            </div>

            <svg width="100%" height="100%" viewBox="0 0 600 400" preserveAspectRatio="xMidYMid meet">
                <defs>
                    <radialGradient id="grad1" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                        <stop offset="0%" style={{ stopColor: 'var(--accent-primary)', stopOpacity: 0.2 }} />
                        <stop offset="100%" style={{ stopColor: 'var(--bg-primary)', stopOpacity: 0 }} />
                    </radialGradient>
                </defs>

                {/* Connections */}
                {nodes.map(node => (
                    <line
                        key={`line-${node.id}`}
                        x1={center.x} y1={center.y}
                        x2={node.x} y2={node.y}
                        stroke={activeNode === node.id ? 'var(--accent-primary)' : 'var(--option-border, #334155)'}
                        strokeWidth={activeNode === node.id ? 2 : 1}
                        style={{ transition: 'stroke 0.3s' }}
                    />
                ))}

                {/* Central Node */}
                <g transform={`translate(${center.x}, ${center.y})`}>
                    <circle cx="0" cy="0" r="60" fill="url(#grad1)" />
                    <circle cx="0" cy="0" r="30" fill="var(--bg-tertiary)" stroke="var(--accent-primary)" strokeWidth="2" />
                    {/* Using simple text instead of Lucide icon inside SVG to avoid foreignObject issues */}
                    <text x="0" y="0" dominantBaseline="middle" textAnchor="middle" fill="var(--accent-primary)" fontSize="14" fontWeight="bold">USER</text>
                    <text x="0" y="50" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="bold">
                        {center.label}
                    </text>
                </g>

                {/* Leaf Nodes */}
                {nodes.map(node => (
                    <g
                        key={node.id}
                        transform={`translate(${node.x}, ${node.y})`}
                        onMouseEnter={() => setActiveNode(node.id)}
                        onMouseLeave={() => setActiveNode(null)}
                        style={{ cursor: 'pointer' }}
                    >
                        <circle
                            cx="0" cy="0" r="24"
                            fill="var(--bg-secondary)"
                            stroke={activeNode === node.id ? 'var(--accent-primary)' : 'var(--border-primary)'}
                            strokeWidth="2"
                            className="transition-all"
                        />
                        {/* Simple text label for icon type */}
                        <text x="0" y="0" dominantBaseline="middle" textAnchor="middle" fill="var(--text-secondary)" fontSize="10" fontWeight="600">
                            {node.type.toUpperCase()}
                        </text>

                        {/* Label */}
                        <text
                            x="0" y="40"
                            textAnchor="middle"
                            fill="var(--text-secondary)"
                            fontSize="11"
                            style={{ opacity: activeNode === node.id ? 1 : 0.7, transition: 'opacity 0.2s' }}
                        >
                            {node.label}
                        </text>
                    </g>
                ))}
            </svg>
        </div>
    );
};

export default NetworkMap;
