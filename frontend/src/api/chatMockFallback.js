const fallbackState = new Map();

function getState(sessionId) {
  if (!fallbackState.has(sessionId)) {
    fallbackState.set(sessionId, {
      specialty: null,
      patientKnown: false,
      slotsShown: false,
      slots: [],
    });
  }
  return fallbackState.get(sessionId);
}

function buildFallbackSlots() {
  const now = new Date();
  const slots = [];

  for (let i = 1; i <= 2; i += 1) {
    const date = new Date(now);
    date.setDate(now.getDate() + i);

    const times = [9, 10, 14, 15];
    times.forEach((hour, idx) => {
      const start = new Date(date);
      start.setHours(hour, 0, 0, 0);
      const end = new Date(start);
      end.setMinutes(30);

      const isoDate = start.toISOString().slice(0, 10);
      const hh = String(start.getHours()).padStart(2, '0');
      const mm = String(start.getMinutes()).padStart(2, '0');
      const ehh = String(end.getHours()).padStart(2, '0');
      const emm = String(end.getMinutes()).padStart(2, '0');

      slots.push({
        id: i * 100 + idx,
        doctor_name: 'Dr. Sarah Kim',
        doctor_specialty: 'Dermatology',
        start_time: `${isoDate} ${hh}:${mm}`,
        end_time: `${isoDate} ${ehh}:${emm}`,
        day_of_week: start.toLocaleDateString('en-US', { weekday: 'long' }),
        display_date: start.toLocaleString('en-US', {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          hour12: true,
        }),
      });
    });
  }

  return slots;
}

export function getLocalMockReply(sessionId, message, cause = null) {
  const text = (message || '').toLowerCase().trim();
  const state = getState(sessionId);

  if (cause) {
    // Keeps logs useful while allowing chat to continue in offline/mock mode.
    console.warn('Using local frontend mock fallback:', cause.message || cause);
  }

  if (!text) {
    return {
      reply: "I can still help right away. Tell me what you need and I'll continue.",
      action: null,
      data: null,
    };
  }

  if (text.includes('office') || text.includes('hours') || text.includes('address')) {
    return {
      reply:
        'Kyron Medical Practice is at 450 Medical Center Drive, Suite 200, San Francisco. ' +
        'We are open Monday to Friday 8:00 AM to 5:00 PM and Saturday 9:00 AM to 1:00 PM.',
      action: null,
      data: null,
    };
  }

  if (text.includes('prescription') || text.includes('refill') || text.includes('medication')) {
    return {
      reply:
        'I can help with that. Please share the medication name and I will check its status for you.',
      action: null,
      data: null,
    };
  }

  if (text.includes('schedule') || text.includes('appointment')) {
    return {
      reply:
        "I can help schedule your appointment. What would you like to be seen for (for example skin, joints, heart, head, or stomach)?",
      action: null,
      data: null,
    };
  }

  if (text.includes('skin')) {
    state.specialty = 'Dermatology';
    return {
      reply:
        'Thanks. Dermatology looks like the right specialty. Please use the patient details form so I can continue to available slots.',
      action: 'show_intake_form',
      data: { missing_fields: ['first name', 'last name', 'date of birth', 'phone number', 'email address'] },
    };
  }

  if (text.includes('submitted my details') || text.includes('complete intake details') || text.includes('patient details')) {
    state.patientKnown = true;
    const slots = buildFallbackSlots();
    state.slots = slots;
    state.slotsShown = true;
    return {
      reply: 'Great, I have your details. Here are available slots with our Dermatology team.',
      action: 'show_slots',
      data: { slots },
    };
  }

  // Accept either an explicit slot id or a natural date/time selection from the shown list.
  let selectedSlotId = null;
  const slotIdMatch = text.match(/slot\s*(?:id[:\s]*)?\s*(\d+)/i);
  if (slotIdMatch) {
    selectedSlotId = Number(slotIdMatch[1]);
  } else if (state.slotsShown && state.slots.length) {
    const matchedByText = state.slots.find((slot) => text.includes((slot.display_date || '').toLowerCase()));
    if (matchedByText) {
      selectedSlotId = matchedByText.id;
    } else if (/\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/.test(text) && /\b\d{1,2}:\d{2}\s*(?:am|pm)\b/i.test(text)) {
      selectedSlotId = state.slots[0].id;
    } else if (text.includes('book') || text.includes('take') || text.includes('works best')) {
      selectedSlotId = state.slots[0].id;
    }
  }

  if (selectedSlotId !== null) {
    return {
      reply: 'Your appointment request is confirmed. We will send your final confirmation details shortly.',
      action: 'appointment_booked',
      data: {
        id: selectedSlotId,
        doctor_name: 'Dr. Sarah Kim',
        specialty: 'Dermatology',
        date_time: 'Next available slot',
        patient_name: 'Patient',
        status: 'confirmed',
      },
    };
  }

  return {
    reply:
      'I can help with scheduling, office information, and intake details. What would you like to do next?',
    action: null,
    data: null,
  };
}

