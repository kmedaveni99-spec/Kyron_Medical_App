import { motion } from 'framer-motion';
import './TypingIndicator.css';

export default function TypingIndicator() {
  return (
    <motion.div
      className="typing-indicator"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <div className="typing-avatar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 8V4H8"/>
          <rect width="16" height="12" x="4" y="8" rx="2"/>
          <path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>
        </svg>
      </div>
      <div className="typing-dots">
        <span className="dot" style={{ animationDelay: '0s' }} />
        <span className="dot" style={{ animationDelay: '0.15s' }} />
        <span className="dot" style={{ animationDelay: '0.3s' }} />
      </div>
    </motion.div>
  );
}

