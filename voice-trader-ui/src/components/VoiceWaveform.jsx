import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';

const VoiceWaveform = ({ isActive = false }) => {
    const bars = 20;
    const canvasRef = useRef(null);

    useEffect(() => {
        if (!isActive || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let animationId;

        const draw = () => {
            const width = canvas.width;
            const height = canvas.height;
            const barWidth = width / bars;

            ctx.clearRect(0, 0, width, height);

            // Draw animated bars
            for (let i = 0; i < bars; i++) {
                // Create wave effect with different frequencies
                const barHeight = Math.sin(Date.now() * 0.003 + i * 0.5) * (height / 3) + height / 3;

                const gradient = ctx.createLinearGradient(0, 0, 0, height);
                gradient.addColorStop(0, 'rgba(37, 99, 235, 0.8)');
                gradient.addColorStop(1, 'rgba(16, 185, 129, 0.4)');

                ctx.fillStyle = gradient;
                ctx.fillRect(
                    i * barWidth + barWidth * 0.2,
                    (height - barHeight) / 2,
                    barWidth * 0.6,
                    barHeight
                );
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationId) cancelAnimationFrame(animationId);
        };
    }, [isActive]);

    if (!isActive) return null;

    return (
        <motion.div
            className="voice-waveform"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
        >
            <canvas
                ref={canvasRef}
                width={200}
                height={60}
                className="waveform-canvas"
            />
        </motion.div>
    );
};

export default VoiceWaveform;
