import { motion } from 'framer-motion';
import '../../App.css'; // Ensure we have access to global styles for now

const BaseCard = ({ children, delay = 0 }) => {
    return (
        <motion.div
            layout
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.4, delay, ease: [0.2, 0, 0, 1] }}
            className="glass-card"
        >
            {children}
        </motion.div>
    );
};

export default BaseCard;
