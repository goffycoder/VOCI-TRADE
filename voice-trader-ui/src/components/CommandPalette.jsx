import { motion, AnimatePresence } from 'framer-motion';
import { X, Command } from 'lucide-react';
import { useEffect, useState } from 'react';

const commands = [
    {
        category: 'Trading',
        items: [
            { key: 'Buy shares', example: '"Buy 10 shares of Reliance"', icon: '📈' },
            { key: 'Sell shares', example: '"Sell 5 shares of TCS"', icon: '📉' },
            { key: 'Check price', example: '"What\'s the price of Infosys?"', icon: '💰' },
        ]
    },
    {
        category: 'Account',
        items: [
            { key: 'Get funds', example: '"Show my available funds"', icon: '💳' },
            { key: 'View holdings', example: '"Show my holdings"', icon: '📊' },
            { key: 'View positions', example: '"Show my positions"', icon: '📋' },
        ]
    },
    {
        category: 'Information',
        items: [
            { key: 'Market news', example: '"Show market news for Reliance"', icon: '📰' },
            { key: 'General news', example: '"What\'s the latest market news?"', icon: '🌐' },
        ]
    },
    {
        category: 'Keyboard Shortcuts',
        items: [
            { key: 'Space', example: 'Activate/Stop voice input', icon: '⌨️' },
            { key: 'Esc', example: 'Close help', icon: '🛑' },
            { key: '?', example: 'Show this help', icon: '❓' },
        ]
    }
];

const CommandPalette = ({ isOpen, onClose }) => {
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        if (isOpen) {
            window.addEventListener('keydown', handleKeyDown);
            return () => window.removeEventListener('keydown', handleKeyDown);
        }
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                className="command-palette-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
            >
                <motion.div
                    className="command-palette"
                    initial={{ opacity: 0, scale: 0.95, y: -20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -20 }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="command-palette-header">
                        <div className="command-palette-title">
                            <Command size={20} />
                            <h2>Voice Commands & Shortcuts</h2>
                        </div>
                        <button onClick={onClose} className="command-palette-close">
                            <X size={20} />
                        </button>
                    </div>

                    <div className="command-palette-content">
                        {commands.map((section, idx) => (
                            <div key={idx} className="command-section">
                                <h3 className="command-category">{section.category}</h3>
                                <div className="command-list">
                                    {section.items.map((item, i) => (
                                        <div key={i} className="command-item">
                                            <span className="command-icon">{item.icon}</span>
                                            <div className="command-details">
                                                <div className="command-key">{item.key}</div>
                                                <div className="command-example">{item.example}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="command-palette-footer">
                        <kbd>Esc</kbd> to close • <kbd>Space</kbd> to activate mic
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default CommandPalette;
