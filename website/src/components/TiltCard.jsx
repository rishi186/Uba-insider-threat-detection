import React, { useRef, useState } from 'react';
import { useTheme } from '../context/ThemeContext';

const TiltCard = ({ children, className = '', style = {} }) => {
    const { lowPowerMode } = useTheme();
    const cardRef = useRef(null);
    const [transform, setTransform] = useState('');

    // If optimizations are on, skip event handlers
    if (lowPowerMode) {
        return (
            <div className={className} style={style}>
                {children}
            </div>
        );
    }

    const handleMouseMove = (e) => {
        if (!cardRef.current) return;

        const card = cardRef.current;
        const rect = card.getBoundingClientRect();

        // Calculate mouse position relative to card center
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        // Max tilt rotation (degrees)
        const maxTilt = 10;

        const rotateX = ((y - centerY) / centerY) * -maxTilt;
        const rotateY = ((x - centerX) / centerX) * maxTilt;

        setTransform(`perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`);
    };

    const handleMouseLeave = () => {
        setTransform('perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
    };

    return (
        <div
            ref={cardRef}
            className={className}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{
                ...style,
                transition: 'transform 0.1s ease-out',
                transform: transform,
                willChange: 'transform'
            }}
        >
            {children}
        </div>
    );
};

export default TiltCard;
