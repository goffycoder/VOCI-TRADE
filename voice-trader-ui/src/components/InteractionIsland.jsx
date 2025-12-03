import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Activity } from 'lucide-react';
import { useState } from 'react';
import VoiceWaveform from './VoiceWaveform';

const InteractionIsland = ({ mode, transcript, onInterrupt }) => {
    const [isHovered, setIsHovered] = useState(false);

    const isListening = mode === 'LISTENING';
    const isProcessing = mode === 'PROCESSING';
    const isSpeaking = mode === 'SPEAKING';

    // Sound Effects placeholders
    const playHoverSound = () => { /* Play hover tick */ };
    const playClickSound = () => { /* Play click confirm */ };

    return (
        <div className="interaction-island">
            {/* Voice Waveform Visualization */}
            <AnimatePresence>
                {isListening && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="waveform-container"
                    >
                        <VoiceWaveform isListening={isListening} />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Transcript Pill */}
            <AnimatePresence mode="wait">
                {(transcript || isProcessing || isSpeaking) && (
                    <motion.div
                        key={mode}
                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="transcript-pill"
                        role="status"
                        aria-live="polite"
                    >
                        {isProcessing ? (
                            <span className="flex items-center gap-2">
                                <Activity className="animate-spin" size={16} />
                                Processing...
                            </span>
                        ) : (
                            transcript
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* The Orb */}
            <motion.button
                className={`orb ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''}`}
                animate={{
                    scale: isHovered ? 1.1 : 1,
                    boxShadow: isListening
                        ? "0 0 40px rgba(239, 68, 68, 0.6)"
                        : isHovered
                            ? "0 0 30px rgba(37, 99, 235, 0.5)"
                            : "0 12px 30px rgba(0, 0, 0, 0.25)"
                }}
                whileTap={{ scale: 0.95 }}
                onHoverStart={() => {
                    setIsHovered(true);
                    playHoverSound();
                }}
                onHoverEnd={() => setIsHovered(false)}
                onClick={() => {
                    playClickSound();
                    onInterrupt();
                }}
                aria-label={isListening ? "Stop listening" : "Start voice command"}
                aria-pressed={isListening}
                title={isListening ? "Stop Listening (Space)" : "Start Listening (Space)"}
            >
                <div className="orb-inner">
                    {isListening ? (
                        <MicOff className="orb-icon text-gray-400" size={32} />
                    ) : (
                        <Mic className="orb-icon text-white" size={32} />
                    )}
                </div>

                {/* Visual Effects */}
                {isListening && (
                    <motion.div
                        className="orb-pulse"
                        animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                    />
                )}

                <div className="orb-glow" />
            </motion.button>
        </div>
    );
};

export default InteractionIsland;
