import { Wallet } from 'lucide-react';
import BaseCard from './BaseCard';

const FundsCard = ({ amount }) => {
    return (
        <BaseCard>
            <div className="cluster-header">
                <Wallet size={14} style={{ marginRight: 6 }} /> Funds
            </div>
            <div className="funds-display">₹{amount}</div>
        </BaseCard>
    );
};

export default FundsCard;
