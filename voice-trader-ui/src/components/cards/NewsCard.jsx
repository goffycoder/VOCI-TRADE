import { Zap } from 'lucide-react';
import BaseCard from './BaseCard';

const NewsCard = ({ content }) => {
    return (
        <BaseCard>
            <div className="cluster-header">
                <Zap size={14} style={{ marginRight: 6 }} /> Market Intelligence
            </div>
            <div className="news-summary">{content}</div>
        </BaseCard>
    );
};

export default NewsCard;
