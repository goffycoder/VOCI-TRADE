import { motion, AnimatePresence } from 'framer-motion';
import { HelpCircle, TrendingUp, Wallet, BarChart3 } from 'lucide-react';
import { useState } from 'react';

const QuickActions = ({ onOpenHelp, onTriggerAction }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const actions = [
        { icon: HelpCircle, label: 'Help', onClick: onOpenHelp, color: '#2563eb' },
        { icon: TrendingUp, label: 'Portfolio', onClick: () => onTriggerAction?.('portfolio'), color: '#10b981' },
        { icon: Wallet, label: 'Funds', onClick: () => onTriggerAction?.('funds'), color: '#f59e0b' },
        { icon: BarChart3, label: 'Positions', onClick: () => onTriggerAction?.('positions'), color: '#8b5cf6' },
    ];

    return (
        <div className="quick-actions">
            <AnimatePresence>
                {isExpanded && actions.map((action, idx) => {
                    const Icon = action.icon;
                    return (
                        <motion.button
                            key={idx}
                            className="quick-action-btn"
                            style={{ backgroundColor: action.color }}
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0, opacity: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            onClick={() => {
                                action.onClick();
                                setIsExpanded(false);
                            }}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            <Icon size={20} />
                            <span className="quick-action-label">{action.label}</span>
                        </motion.button>
                    );
                })}
            </AnimatePresence>

            <motion.button
                className="quick-actions-fab"
                onClick={() => setIsExpanded(!isExpanded)}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                animate={{ rotate: isExpanded ? 45 : 0 }}
            >
                <HelpCircle size={24} />
            </motion.button>
        </div>
    );
};

export default QuickActions;
