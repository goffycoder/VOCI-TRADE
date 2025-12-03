import { motion } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';

const ChatCard = ({ content }) => {
    return (
        <motion.div
            className="card chat-card"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
            <div className="card-header">
                <div className="icon-badge bg-gradient-to-r from-indigo-500 to-purple-500">
                    <Sparkles size={18} color="white" />
                </div>
                <span className="card-title">AI Insight</span>
            </div>

            <div className="card-content">
                <p className="text-lg leading-relaxed text-gray-100 font-medium">
                    {content}
                </p>
            </div>

            {/* Decorative decorative footer */}
            <div className="card-footer">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                    <Bot size={12} />
                    <span>Generated based on live context</span>
                </div>
            </div>

            <style jsx>{`
                .chat-card {
                    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                    border: 1px solid rgba(139, 92, 246, 0.2);
                    padding: 1.25rem;
                }
                .icon-badge {
                    padding: 6px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
            `}</style>
        </motion.div>
    );
};

export default ChatCard;