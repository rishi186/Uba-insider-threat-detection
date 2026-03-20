import React, { useState } from 'react';
import DecryptText from './DecryptText';

const RedactedText = ({ text, className = '', revealed = false }) => {
    const [isHovered, setIsHovered] = useState(false);
    const isVisible = isHovered || revealed;

    if (!text) return null;

    return (
        <span
            className={`redacted-wrapper ${className}`}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                position: 'relative'
            }}
            title="Hover to decrypt"
        >
            {isVisible ? (
                <span style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>
                    <DecryptText text={text} />
                </span>
            ) : (
                <span style={{
                    color: 'var(--text-muted)',
                    letterSpacing: '-2px',
                    opacity: 0.7
                }}>
                    {'█'.repeat(Math.min(text.length, 12))}
                </span>
            )}
        </span>
    );
};

export default RedactedText;
