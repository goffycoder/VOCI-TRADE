import BaseCard from './BaseCard';

const TextCard = ({ content }) => {
    return (
        <BaseCard>
            <div className="text-gray-200 text-lg leading-relaxed whitespace-pre-wrap">
                {content}
            </div>
        </BaseCard>
    );
};

export default TextCard;
