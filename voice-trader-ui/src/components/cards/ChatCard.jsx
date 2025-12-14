import BaseCard from './BaseCard';
import { Sparkles } from 'lucide-react';

const ChatCard = ({ content }) => {
    return (
        <BaseCard>
            <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 shrink-0">
                    <Sparkles size={18} className="text-indigo-400" />
                </div>
                <div className="flex-1">
                    <div className="text-xs font-medium text-indigo-300 mb-1 uppercase tracking-wider">AI Assistant</div>
                    <p className="text-gray-200 leading-relaxed text-sm">
                        {content}
                    </p>
                </div>
            </div>
        </BaseCard>
    );
};

export default ChatCard;