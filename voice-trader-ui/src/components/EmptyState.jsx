import { motion } from 'framer-motion';
import { Mic, Sparkles } from 'lucide-react';

const EmptyState = () => {
    return (
        <motion.div
            className="empty-state"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
        >
            <motion.div
                className="empty-icon"
                animate={{
                    scale: [1, 1.05, 1],
                    rotate: [0, 5, -5, 0]
                }}
                transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "easeInOut"
                }}
            >
                <Sparkles size={48} strokeWidth={1.5} />
            </motion.div>

            <h2>Ready to Trade</h2>
            <p>
                Press <kbd>Space</kbd> or tap the microphone to start
            </p>

            <div className="example-commands">
                <div className="command-chip">
                    <Mic size={14} />
                    <span>"What's the price of Reliance?"</span>
                </div>
                <div className="command-chip">
                    <Mic size={14} />
                    <span>"Buy 10 shares of TCS"</span>
                </div>
                <div className="command-chip">
                    <Mic size={14} />
                    <span>"Show me market news"</span>
                </div>
            </div>
        </motion.div>
    );
};

export default EmptyState;
