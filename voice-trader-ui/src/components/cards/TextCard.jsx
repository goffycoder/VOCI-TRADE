import BaseCard from './BaseCard';

const TextCard = ({ content }) => {
    return (
        <BaseCard>
            <div style={{ fontSize: '1.1rem', color: '#444' }}>{content}</div>
        </BaseCard>
    );
};

export default TextCard;
