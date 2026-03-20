import React, { useEffect, useRef, useState } from 'react';

const CustomCursor = () => {
    const cursorRef = useRef(null);
    const cursorDotRef = useRef(null);
    const [isHovering, setIsHovering] = useState(false);
    const [isClicked, setIsClicked] = useState(false);

    useEffect(() => {
        const cursor = cursorRef.current;
        const cursorDot = cursorDotRef.current;

        const moveCursor = (e) => {
            const { clientX, clientY } = e;

            // Main ring follows with slight delay (using CSS transition or requestAnimationFrame)
            // But direct update is snappier for "interaction" feeling
            cursor.style.transform = `translate3d(${clientX - 20}px, ${clientY - 20}px, 0)`;
            cursorDot.style.transform = `translate3d(${clientX - 4}px, ${clientY - 4}px, 0)`;
        };

        const handleMouseDown = () => setIsClicked(true);
        const handleMouseUp = () => setIsClicked(false);

        const handleLinkHover = () => setIsHovering(true);
        const handleLinkLeave = () => setIsHovering(false);

        document.addEventListener('mousemove', moveCursor);
        document.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mouseup', handleMouseUp);

        // Add hover listeners to clickable elements
        const clickables = document.querySelectorAll('a, button, input, select, .clickable');
        clickables.forEach(el => {
            el.addEventListener('mouseenter', handleLinkHover);
            el.addEventListener('mouseleave', handleLinkLeave);
        });

        // Dynamic observer for new elements (like in single page apps) could be added here
        // For now, let's just stick to the global listen

        return () => {
            document.removeEventListener('mousemove', moveCursor);
            document.removeEventListener('mousedown', handleMouseDown);
            document.removeEventListener('mouseup', handleMouseUp);
            clickables.forEach(el => {
                el.removeEventListener('mouseenter', handleLinkHover);
                el.removeEventListener('mouseleave', handleLinkLeave);
            });
        };
    }, []);

    return (
        <>
            <div
                ref={cursorRef}
                className={`custom-cursor-ring ${isHovering ? 'hover' : ''} ${isClicked ? 'clicked' : ''}`}
            />
            <div
                ref={cursorDotRef}
                className={`custom-cursor-dot ${isHovering ? 'hover' : ''}`}
            />
        </>
    );
};

export default CustomCursor;
