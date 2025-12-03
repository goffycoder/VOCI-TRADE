import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Package } from 'lucide-react';
import BaseCard from './BaseCard';

const PortfolioCard = ({ content }) => {
    // Parse the holdings text
    // Example: "You are holding: 10 shares of RELIANCE, 5 shares of TCS."

    return (
        <BaseCard>
            <motion.div
                className="portfolio-card"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <div className="card-header">
                    <Package size={20} className="card-icon" />
                    <h3>Your Holdings</h3>
                </div>

                <div className="card-content">
                    <p className="holdings-text">{content}</p>
                </div>
            </motion.div>
        </BaseCard>
    );
};

export default PortfolioCard;
