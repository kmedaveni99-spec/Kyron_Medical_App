import { useState } from 'react';
import { motion } from 'framer-motion';
import { Phone, X, PhoneCall, AlertCircle } from 'lucide-react';
import { initiateVoiceCall } from '../api/client';
import './VoiceCallModal.css';

export default function VoiceCallModal({ sessionId, defaultPhone, onClose }) {
  const [phone, setPhone] = useState(defaultPhone || '');
  const [status, setStatus] = useState('idle'); // idle, calling, success, queued, error
  const [error, setError] = useState('');

  const handleCall = async () => {
    if (!phone.trim()) {
      setError('Please enter your phone number');
      return;
    }

    setStatus('calling');
    setError('');

    try {
      const result = await initiateVoiceCall(sessionId, phone);
      if (result.success) {
        setStatus(result.queued ? 'queued' : 'success');
      } else {
        setStatus('error');
        setError(result.error || 'Unable to initiate call. Please try again.');
      }
    } catch (err) {
      setStatus('error');
      setError('Connection error. Please check your network and try again.');
    }
  };

  return (
    <motion.div
      className="modal-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="voice-modal glass-card"
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={onClose}>
          <X size={18} />
        </button>

        <div className="modal-icon">
          {status === 'success' ? (
            <motion.div
              className="icon-ring success"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', damping: 12 }}
            >
              <PhoneCall size={28} />
            </motion.div>
          ) : (
            <div className="icon-ring">
              <Phone size={28} />
            </div>
          )}
        </div>

        <h2 className="modal-title">
          {status === 'success' ? 'Call Incoming!' : status === 'queued' ? 'Request Received' : 'Continue on Phone'}
        </h2>
        <p className="modal-desc">
          {status === 'success'
            ? 'Your phone should be ringing shortly. The AI will continue your conversation with full context.'
            : status === 'queued'
              ? 'We have logged your callback request safely and will follow up shortly.'
            : 'We\'ll call your phone so you can continue this conversation with our AI voice assistant. The AI will remember everything from this chat.'}
        </p>

        {status !== 'success' && status !== 'queued' && (
          <>
            <div className="phone-input-group">
              <Phone size={16} className="phone-icon" />
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (555) 123-4567"
                className="phone-input"
                disabled={status === 'calling'}
              />
            </div>

            {error && (
              <motion.div
                className="error-msg"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={14} />
                {error}
              </motion.div>
            )}

            <button
              className="call-btn btn-primary"
              onClick={handleCall}
              disabled={status === 'calling'}
            >
              {status === 'calling' ? (
                <>
                  <span className="spinner" />
                  Connecting...
                </>
              ) : (
                <>
                  <Phone size={16} />
                  Call Me Now
                </>
              )}
            </button>
          </>
        )}

        {(status === 'success' || status === 'queued') && (
          <button className="call-btn btn-glass" onClick={onClose}>
            Got it
          </button>
        )}
      </motion.div>
    </motion.div>
  );
}

