import { TrendingUp, TrendingDown } from 'lucide-react';
import BaseCard from './BaseCard';

const MarketWatchCard = ({ data }) => {
    return (
        <BaseCard>
            <div className="cluster-header">
                <TrendingUp size={14} style={{ marginRight: 6 }} /> Market Watch
            </div>
            {data.map((stock, idx) => (
                <div key={idx} className="price-info">
                    <span className="stock-symbol">{stock.symbol}</span>
                    <span className="price-value">₹{stock.price}</span>
                    <div className={`price-change ${stock.change === 'up' ? 'up' : 'down'}`}>
                        {stock.change === 'up' ? (
                            <TrendingUp size={16} aria-label="Price up" />
                        ) : (
                            <TrendingDown size={16} aria-label="Price down" />
                        )}
                        <span>{stock.change === 'up' ? '+0.5%' : '-0.5%'}</span>
                    </div>
                </div>
            ))}
        </BaseCard>
    );
};

export default MarketWatchCard;
