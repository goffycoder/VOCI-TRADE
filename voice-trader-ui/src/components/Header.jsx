import { TrendingUp, Wifi, WifiOff, Settings } from 'lucide-react';
import { motion } from 'framer-motion';

const Header = ({ isConnected = true }) => {
    return (
        <motion.header
            className="app-header"
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
        >
            <div className="header-content">
                {/* Branding */}
                <div className="brand">
                    <TrendingUp size={24} strokeWidth={2.5} />
                    <h1>Voice Trader</h1>
                </div>

                {/* Right Side Actions */}
                <div className="header-actions">
                    {/* Connection Status */}
                    <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                        {isConnected ? (
                            <>
                                <Wifi size={16} />
                                <span>Live</span>
                            </>
                        ) : (
                            <>
                                <WifiOff size={16} />
                                <span>Offline</span>
                            </>
                        )}
                    </div>

                    {/* Settings */}
                    <button className="header-icon-btn" aria-label="Settings">
                        <Settings size={20} />
                    </button>
                </div>
            </div>
        </motion.header>
    );
};

export default Header;
