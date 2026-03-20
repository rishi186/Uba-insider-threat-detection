import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '../context/ThemeContext';

const MatrixBackground = () => {
    // Optimization: Disable if Low Power Mode is on
    const { lowPowerMode } = useTheme();

    if (lowPowerMode) return null;

    const canvasRef = useRef(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        const columns = Math.floor(width / 20);
        const drops = [];
        const chars = '01';

        // Initialize drops
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -100;
        }

        const handleResize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            // Re-calc columns if needed, or better, just extend the array
            const newColumns = Math.floor(width / 20);
            while (drops.length < newColumns) {
                drops.push(Math.random() * -100);
            }
        };

        const handleMouseMove = (e) => {
            setMousePos({ x: e.clientX, y: e.clientY });
        };

        window.addEventListener('resize', handleResize);
        window.addEventListener('mousemove', handleMouseMove);

        const draw = () => {
            // Semi-transparent black to create trail effect
            ctx.fillStyle = 'rgba(10, 15, 28, 0.1)';
            ctx.fillRect(0, 0, width, height);

            ctx.font = '15px "JetBrains Mono", monospace';

            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                const x = i * 20;
                const y = drops[i] * 20;

                // Mouse interaction distance
                const dx = x - mousePos.x;
                const dy = y - mousePos.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                // Color logic
                if (dist < 150) {
                    ctx.fillStyle = '#ffffff'; // White highlight near mouse
                    ctx.shadowBlur = 10;
                    ctx.shadowColor = '#06b6d4';
                } else {
                    ctx.fillStyle = '#06b6d4'; // Theme cyan
                    ctx.shadowBlur = 0;
                }

                ctx.fillText(text, x, y);

                // Reset drop or move it down
                if (y > height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
            requestAnimationFrame(draw);
        };

        const animationId = requestAnimationFrame(draw);

        return () => {
            cancelAnimationFrame(animationId);
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('mousemove', handleMouseMove);
        };
    }, [mousePos]); // Re-bind effect if mousePos changes? No, tracking via ref or state in render loop is better.
    // Actually, relying on state inside the draw loop closure might catch old state if not careful.
    // Let's use a ref for mouse position to avoid re-triggering the effect loop constantly.

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                zIndex: 0, // Behind content but in front of body bg
                pointerEvents: 'none' // Let clicks pass through
            }}
        />
    );
};

// Optimization: Use ref for mouse pos to avoid effect re-run
const MatrixBackgroundOptimized = () => {
    const canvasRef = useRef(null);
    const mouseRef = useRef({ x: 0, y: 0 });

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        const fontSize = 16;
        const columns = Math.ceil(width / fontSize);
        const drops = new Array(columns).fill(1);
        const chars = '01';

        const handleResize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            const newColumns = Math.ceil(width / fontSize);
            while (drops.length < newColumns) {
                drops.push(0);
            }
        };

        const handleMouseMove = (e) => {
            mouseRef.current = { x: e.clientX, y: e.clientY };
        };

        window.addEventListener('resize', handleResize);
        window.addEventListener('mousemove', handleMouseMove);

        let animationId;

        const draw = () => {
            // Trail effect
            ctx.fillStyle = 'rgba(10, 15, 28, 0.1)';
            ctx.fillRect(0, 0, width, height);

            ctx.font = `${fontSize}px "JetBrains Mono", monospace`;

            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                const x = i * fontSize;
                const y = drops[i] * fontSize;

                // Mouse interaction
                const dx = x - mouseRef.current.x;
                const dy = y - mouseRef.current.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 100) {
                    ctx.fillStyle = '#fff';     // Highlight color
                    ctx.shadowBlur = 15;
                    ctx.shadowColor = '#06b6d4';
                } else {
                    // Random variations of cyan/greenish
                    ctx.fillStyle = Math.random() > 0.95 ? '#22c55e' : '#06b6d4';
                    ctx.shadowBlur = 0;
                }

                ctx.fillText(text, x, y);

                if (y > height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
            animationId = requestAnimationFrame(draw);
        };

        animationId = requestAnimationFrame(draw);

        return () => {
            cancelAnimationFrame(animationId);
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('mousemove', handleMouseMove);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="matrix-bg"
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                zIndex: -1,
                pointerEvents: 'none',
                opacity: 0.8
            }}
        />
    );
};

export default MatrixBackgroundOptimized;
