import { useState } from 'react';
import { motion } from 'framer-motion';
import { submitIntake } from '../api/client';
import './IntakeFormCard.css';

const INITIAL_FORM = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  phone: '',
  email: '',
  reason: '',
  sms_opt_in: false,
};

export default function IntakeFormCard({ sessionId, onSubmitted, onClose }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const onChange = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.first_name || !form.last_name || !form.date_of_birth || !form.phone || !form.email || !form.reason) {
      setError('Please complete all required fields.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await submitIntake({ ...form, session_id: sessionId });
      onSubmitted?.(response, form);
      setForm(INITIAL_FORM);
    } catch (submitError) {
      setError(submitError.message || 'Failed to submit details. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      className="intake-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className="intake-header">
        <h3>Patient Details</h3>
        <button type="button" className="intake-close" onClick={onClose}>Close</button>
      </div>

      <form className="intake-form" onSubmit={handleSubmit}>
        <div className="intake-grid">
          <input
            type="text"
            placeholder="First name"
            value={form.first_name}
            onChange={(e) => onChange('first_name', e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Last name"
            value={form.last_name}
            onChange={(e) => onChange('last_name', e.target.value)}
            required
          />
          <input
            type="date"
            value={form.date_of_birth}
            onChange={(e) => onChange('date_of_birth', e.target.value)}
            required
          />
          <input
            type="tel"
            placeholder="Phone number"
            value={form.phone}
            onChange={(e) => onChange('phone', e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => onChange('email', e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Reason for visit"
            value={form.reason}
            onChange={(e) => onChange('reason', e.target.value)}
            required
          />
        </div>

        <label className="intake-checkbox">
          <input
            type="checkbox"
            checked={form.sms_opt_in}
            onChange={(e) => onChange('sms_opt_in', e.target.checked)}
          />
          Receive SMS appointment updates
        </label>

        {error && <p className="intake-error">{error}</p>}

        <button type="submit" className="intake-submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting...' : 'Submit Details'}
        </button>
      </form>
    </motion.div>
  );
}

