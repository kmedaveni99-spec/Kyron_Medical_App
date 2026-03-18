import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Phone, Calendar, MapPin, Pill, Sparkles } from 'lucide-react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import VoiceCallModal from './VoiceCallModal';
import SlotPicker from './SlotPicker';
import { sendMessage } from '../api/client';
import './ChatWindow.css';

const QUICK_ACTIONS = [
  { icon: <Calendar size={15} />, label: 'Schedule Appointment', message: 'I would like to schedule an appointment' },
  { icon: <Pill size={15} />, label: 'Prescription Refill', message: 'I need to check on a prescription refill' },
  { icon: <MapPin size={15} />, label: 'Office Info', message: 'What are your office hours and address?' },
];

export default function ChatWindow({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [patientPhone, setPatientPhone] = useState('');
  const [showSlots, setShowSlots] = useState(null);
  const [hasStarted, setHasStarted] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Send initial greeting
  useEffect(() => {
    if (!hasStarted) {
      setHasStarted(true);
      handleSend('Hello');
    }
  }, []);

  const handleSend = async (messageText) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    if (!messageText) {
      setMessages(prev => [...prev, { role: 'user', content: text }]);
    }
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendMessage(sessionId, text);

      if (response.reply) {
        setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
      }

      // Handle UI actions from the backend
      if (response.action === 'show_slots' && response.data?.slots) {
        setShowSlots(response.data.slots);
      }

      if (response.action === 'appointment_booked' && response.data) {
        setShowSlots(null);
        setMessages(prev => [...prev, {
          role: 'system',
          content: 'appointment_booked',
          data: response.data
        }]);
      }

      // Capture patient phone for voice call
      if (response.data?.patient_phone) {
        setPatientPhone(response.data.patient_phone);
      }

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm sorry, I'm having trouble connecting right now. Please try again in a moment."
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSlotSelect = async (slot) => {
    setShowSlots(null);
    const msg = `I'd like to book the appointment on ${slot.display_date} (slot ID: ${slot.id})`;
    setMessages(prev => [...prev, { role: 'user', content: `I'll take the ${slot.display_date} slot` }]);
    setIsLoading(true);

    try {
      const response = await sendMessage(sessionId, msg);
      if (response.reply) {
        setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
      }
      if (response.action === 'appointment_booked' && response.data) {
        setMessages(prev => [...prev, {
          role: 'system',
          content: 'appointment_booked',
          data: response.data
        }]);
      }
    } catch (error) {
      console.error('Booking error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const showQuickActions = messages.length <= 1;

  return (
    <div className="chat-container glass-card">
      {/* Messages Area */}
      <div className="messages-area">
        <AnimatePresence mode="popLayout">
          {messages.map((msg, idx) => (
            <MessageBubble key={idx} message={msg} />
          ))}
        </AnimatePresence>

        {/* Slot Picker */}
        {showSlots && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="slot-picker-wrapper"
          >
            <SlotPicker slots={showSlots} onSelect={handleSlotSelect} />
          </motion.div>
        )}

        {isLoading && <TypingIndicator />}

        {/* Quick Actions */}
        {showQuickActions && !isLoading && messages.length === 1 && (
          <motion.div
            className="quick-actions"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
          >
            {QUICK_ACTIONS.map((action, idx) => (
              <button
                key={idx}
                className="quick-action-btn"
                onClick={() => {
                  setMessages(prev => [...prev, { role: 'user', content: action.message }]);
                  handleSend(action.message);
                }}
              >
                {action.icon}
                <span>{action.label}</span>
              </button>
            ))}
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <div className="input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="chat-input"
            disabled={isLoading}
          />
          <div className="input-actions">
            <button
              className="voice-call-btn"
              onClick={() => setShowVoiceModal(true)}
              title="Continue on phone call"
            >
              <Phone size={18} />
            </button>
            <button
              className="send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
        <p className="input-hint">
          <Sparkles size={12} /> AI assistant · Cannot provide medical advice
        </p>
      </div>

      {/* Voice Call Modal */}
      <AnimatePresence>
        {showVoiceModal && (
          <VoiceCallModal
            sessionId={sessionId}
            defaultPhone={patientPhone}
            onClose={() => setShowVoiceModal(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

