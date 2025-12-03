import { useRef, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import MarketWatchCard from './cards/MarketWatchCard';
import FundsCard from './cards/FundsCard';
import NewsCard from './cards/NewsCard';
import TextCard from './cards/TextCard';
import PortfolioCard from './cards/PortfolioCard';
import PositionCard from './cards/PositionCard';
import EmptyState from './EmptyState';

const HistoryFeed = ({ history, isLoading = false }) => {
    const canvasRef = useRef(null);
    const cardsRef = useRef([]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (canvasRef.current) {
            canvasRef.current.scrollTop = canvasRef.current.scrollHeight;
        }
    }, [history]);

    // Keyboard Navigation
    const handleKeyDown = (e, index) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextCard = cardsRef.current[index + 1];
            if (nextCard) nextCard.focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prevCard = cardsRef.current[index - 1];
            if (prevCard) prevCard.focus();
        }
    };

    return (
        <div
            className="canvas-container"
            ref={canvasRef}
            role="feed"
            aria-label="Conversation history"
        >
            <div className="stack-grid">
                <AnimatePresence mode="popLayout">
                    {history.length === 0 ? (
                        <EmptyState />
                    ) : (
                        history.map((card, index) => {
                            const CardComponent = {
                                'PRICE_CLUSTER': MarketWatchCard,
                                'FUNDS': FundsCard,
                                'NEWS': NewsCard,
                                'HOLDINGS': PortfolioCard,
                                'POSITIONS': PositionCard,
                                'TEXT': TextCard
                            }[card.type] || TextCard;

                            const props = {
                                'PRICE_CLUSTER': { data: card.data },
                                'FUNDS': { amount: card.content },
                                'NEWS': { content: card.content },
                                'HOLDINGS': { content: card.content },
                                'POSITIONS': { content: card.content },
                                'TEXT': { content: card.content }
                            }[card.type] || { content: card.content };

                            return (
                                <div
                                    key={card.id}
                                    ref={el => cardsRef.current[index] = el}
                                    tabIndex={0}
                                    onKeyDown={(e) => handleKeyDown(e, index)}
                                    className="card-wrapper focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-xl"
                                    role="article"
                                    aria-label={`${card.type.toLowerCase().replace('_', ' ')} card`}
                                >
                                    <CardComponent {...props} />
                                </div>
                            );
                        })
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default HistoryFeed;
