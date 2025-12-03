import { motion } from 'framer-motion';

const SkeletonCard = ({ delay = 0 }) => (
    <motion.div
        className="skeleton-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay }}
    >
        <div className="skeleton-line skeleton-header" />
        <div className="skeleton-line skeleton-text" />
        <div className="skeleton-line skeleton-text short" />
    </motion.div>
);

const LoadingState = ({ count = 3 }) => {
    return (
        <div className="loading-state">
            {[...Array(count)].map((_, i) => (
                <SkeletonCard key={i} delay={i * 0.1} />
            ))}
        </div>
    );
};

export default LoadingState;
