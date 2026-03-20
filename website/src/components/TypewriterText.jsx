import React, { useState, useEffect } from 'react';

const TypewriterText = ({ text, speed = 50, delay = 0 }) => {
    const [displayedText, setDisplayedText] = useState('');
    const [showCursor, setShowCursor] = useState(true);

    useEffect(() => {
        setDisplayedText(''); // Reset on text change
        let currentIndex = 0;
        let timeoutId;

        const typeChar = () => {
            if (currentIndex < text.length) {
                setDisplayedText(text.slice(0, currentIndex + 1));
                currentIndex++;
                timeoutId = setTimeout(typeChar, speed);
            }
        };

        const startTimeout = setTimeout(() => {
            typeChar();
        }, delay);

        return () => {
            clearTimeout(timeoutId);
            clearTimeout(startTimeout);
        };
    }, [text, speed, delay]);

    // Blinking cursor effect
    useEffect(() => {
        const cursorInterval = setInterval(() => {
            setShowCursor(prev => !prev);
        }, 530);
        return () => clearInterval(cursorInterval);
    }, []);

    return (
        <span className="mono" style={{ display: 'inline-flex', alignItems: 'center' }}>
            {displayedText}
            <span style={{
                opacity: showCursor ? 1 : 0,
                marginLeft: '2px',
                color: 'var(--accent-primary)'
            }}>_</span>
        </span>
    );
};

export default TypewriterText;
