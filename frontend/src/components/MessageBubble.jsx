import { motion } from 'framer-motion';
import { Bot, User, CheckCircle, Calendar, MapPin } from 'lucide-react';
import './MessageBubble.css';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  // Appointment booked card
  if (isSystem && message.content === 'appointment_booked' && message.data) {
    const appt = message.data;
    return (
      <motion.div
        className="appointment-card"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        <div className="appt-header">
          <CheckCircle size={20} />
          <span>Appointment Confirmed</span>
        </div>
        <div className="appt-details">
          <div className="appt-row">
            <Calendar size={14} />
            <span>{appt.date_time}</span>
          </div>
          <div className="appt-row">
            <User size={14} />
            <span>{appt.doctor_name} — {appt.specialty}</span>
          </div>
          <div className="appt-row">
            <MapPin size={14} />
            <span>450 Medical Center Dr, Suite 200, SF</span>
          </div>
        </div>
      </motion.div>
    );
  }

  if (isSystem) return null;

  return (
    <motion.div
      className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
    >
      {!isUser && (
        <div className="avatar ai-avatar">
          <Bot size={16} />
        </div>
      )}
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
        <p className="message-text">{message.content}</p>
      </div>
      {isUser && (
        <div className="avatar user-avatar">
          <User size={16} />
        </div>
      )}
    </motion.div>
  );
}

