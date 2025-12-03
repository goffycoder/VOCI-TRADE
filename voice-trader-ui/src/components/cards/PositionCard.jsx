import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import BaseCard from './BaseCard';

const PositionCard = ({ content }) => {
    // Parse P&L from content
    // Example: "Total intraday P&L is a profit of 1250.50 rupees. Active: RELIANCE (500.00), TCS (750.50)."
    const isProfit = content.toLowerCase().includes('profit');
    const isProfitable = isProfit;

    // Extract P&L amount 
    const plMatch = content.match(/(profit|loss) of ([\d,]+\.?\d*)/i);
    const plAmount = plMatch ? plMatch[2] : '0.00';

    return (
        <BaseCard>
            <motion.div
                className="position-card"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <div className="card-header">
                    <Activity size={20} className="card-icon" />
                    <h3>Open Positions</h3>
                </div>

                <div className="card-content">
                    <div className={`pnl-display ${isProfitable ? 'profit' : 'loss'}`}>
                        {/* Icon provides shape cue for color blind users */}
                        {isProfitable ? <TrendingUp size={24} aria-label="Profit" /> : <TrendingDown size={24} aria-label="Loss" />}
                        <div className="pnl-amount">
                            <span className="pnl-label">{isProfitable ? 'Profit' : 'Loss'}</span>
                            <span className="pnl-value">₹{plAmount}</span>
                        </div>
                    </div>

                    <p className="positions-text">{content}</p>
                </div>
            </motion.div>
        </BaseCard>
    );
};

export default PositionCard;
