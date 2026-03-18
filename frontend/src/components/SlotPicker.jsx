import { motion } from 'framer-motion';
import { Calendar, Clock } from 'lucide-react';
import './SlotPicker.css';

export default function SlotPicker({ slots, onSelect }) {
  // Group slots by date
  const grouped = {};
  slots.forEach(slot => {
    const date = slot.start_time.split(' ')[0];
    if (!grouped[date]) {
      grouped[date] = { day: slot.day_of_week, date, slots: [] };
    }
    grouped[date].slots.push(slot);
  });

  return (
    <div className="slot-picker">
      <div className="slot-picker-header">
        <Calendar size={16} />
        <span>Available Appointments</span>
      </div>
      <div className="slot-groups">
        {Object.entries(grouped).map(([date, group], gi) => (
          <motion.div
            key={date}
            className="slot-group"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: gi * 0.1 }}
          >
            <div className="slot-date-label">
              {group.day}, {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </div>
            <div className="slot-times">
              {group.slots.map(slot => {
                const time = slot.start_time.split(' ')[1];
                const [h, m] = time.split(':').map(Number);
                const ampm = h >= 12 ? 'PM' : 'AM';
                const hour12 = h > 12 ? h - 12 : h === 0 ? 12 : h;
                return (
                  <button
                    key={slot.id}
                    className="slot-time-btn"
                    onClick={() => onSelect(slot)}
                  >
                    <Clock size={12} />
                    {hour12}:{m.toString().padStart(2, '0')} {ampm}
                  </button>
                );
              })}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

