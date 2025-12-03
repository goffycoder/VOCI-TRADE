import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useEffect, useState } from 'react';

const icons = {
    success: CheckCircle,
    error: XCircle,
    info: Info,
    warning: AlertTriangle,
};

const NotificationToast = ({ message, type = 'info', onClose, duration = 3000 }) => {
    const [progress, setProgress] = useState(100);
    const Icon = icons[type];

    useEffect(() => {
        if (duration <= 0) return;

        const interval = 50;
        const decrement = (100 * interval) / duration;

        const timer = setInterval(() => {
            setProgress(prev => {
                const next = prev - decrement;
                return next <= 0 ? 0 : next;
            });
        }, interval);

        return () => clearInterval(timer);
    }, [duration]);

    return (
        <motion.div
            className={`toast toast-${type}`}
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
            layout
        >
            <div className="toast-content">
                <Icon size={20} className="toast-icon" />
                <span className="toast-message">{message}</span>
                <button onClick={onClose} className="toast-close" aria-label="Close">
                    <X size={16} />
                </button>
            </div>
            {duration > 0 && (
                <div className="toast-progress">
                    <motion.div
                        className="toast-progress-bar"
                        initial={{ width: '100%' }}
                        animate={{ width: `${progress}%` }}
                        transition={{ ease: 'linear' }}
                    />
                </div>
            )}
        </motion.div>
    );
};

export default NotificationToast;
