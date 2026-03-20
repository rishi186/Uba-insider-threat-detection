import React, { useState, useEffect } from 'react';

const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()';

const DecryptText = ({ text, className = '' }) => {
    const [display, setDisplay] = useState('');
    const [isFinished, setIsFinished] = useState(false);

    useEffect(() => {
        // Handle non-string inputs (like numbers)
        const target = String(text);
        let iteration = 0;

        setIsFinished(false);

        const interval = setInterval(() => {
            setDisplay(
                target.split('')
                    .map((char, index) => {
                        if (index < iteration) {
                            return target[index];
                        }
                        return characters[Math.floor(Math.random() * characters.length)];
                    })
                    .join('')
            );

            if (iteration >= target.length) {
                clearInterval(interval);
                setIsFinished(true);
            }

            iteration += 1 / 3; // Speed control
        }, 30);

        return () => clearInterval(interval);
    }, [text]);

    return (
        <span className={`${className} ${isFinished ? '' : 'mono'}`}>
            {display}
        </span>
    );
};

export default DecryptText;
