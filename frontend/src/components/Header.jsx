import { motion } from 'framer-motion';
import './Header.css';

export default function Header() {
  return (
    <motion.header
      className="header"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <div className="header-left">
        <img src="/kyron_logo.jpeg" alt="Kyron Medical" className="logo-img" />
        <div className="header-text">
          <h1 className="logo-text">Kyron Medical</h1>
          <span className="logo-subtitle">AI Patient Assistant</span>
        </div>
      </div>
      <div className="header-right">
        <div className="status-indicator">
          <span className="status-dot" />
          <span className="status-text">Online</span>
        </div>
      </div>
    </motion.header>
  );
}
