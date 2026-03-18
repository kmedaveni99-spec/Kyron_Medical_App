# Kyron Medical AI - Patient Assistant

An intelligent, patient-facing AI web application for Kyron Medical Practice. Patients can chat with a human-like AI assistant to schedule appointments, check prescription refills, get office information, and seamlessly transition to a voice call.

![Kyron Medical](https://img.shields.io/badge/Kyron-Medical-0A6EBD?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)

## ✨ Features

### Core Workflows
- **🗓 Appointment Scheduling** — AI-guided intake → doctor matching → slot selection → booking with confirmation
- **💊 Prescription Refills** — Check refill status for medications
- **📍 Office Information** — Hours, address, contact details, provider directory
- **📞 Voice Call Handoff** — Click a button to receive a phone call and continue the conversation with the same AI, retaining full chat context

### AI Capabilities
- **Semantic Doctor Matching** — Describes a body part or condition → matched to the right specialist
- **Natural Date Understanding** — "Do you have something on a Tuesday?" → filters slots
- **Safety Guardrails** — Cannot provide medical advice, diagnoses, or treatment recommendations
- **5 Specialists**: Orthopedics, Cardiology, Dermatology, Neurology, Gastroenterology

### Notifications
- **📧 Email Confirmation** — Branded HTML email via SendGrid upon booking
- **📱 SMS Confirmation** — Opt-in text message via Twilio upon booking

### UI/UX
- **Liquid Glass Design** — Frosted glass cards, animated gradient backgrounds, floating orbs
- **Kyron Medical Branding** — Blue (#0A6EBD) and Teal (#12A89D) color palette
- **Framer Motion Animations** — Smooth message transitions, typing indicators
- **Responsive Design** — Works on desktop and mobile

## 🏗 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, Framer Motion, Lucide Icons |
| **Backend** | Python FastAPI, SQLAlchemy (async), SQLite |
| **AI** | OpenAI GPT-4o with Function Calling |
| **Voice** | Twilio Voice (outbound calls + TwiML webhooks) |
| **Email** | SendGrid |
| **SMS** | Twilio Messaging |
| **Deployment** | Docker Compose, Nginx, AWS EC2 |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- OpenAI API key

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/Kyron-AI-App.git
cd Kyron-AI-App
```

### 2. Configure Environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 3. Start Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Open App
Navigate to `http://localhost:5173`

## 🐳 Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Access at http://localhost
```

## 📁 Project Structure

```
Kyron-AI-App/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── models.py            # ORM models (Patient, Doctor, Appointment, etc.)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── seed.py              # Database seeding (doctors + 45 days of slots)
│   │   ├── routes/
│   │   │   ├── chat.py          # Main chat endpoint with tool execution
│   │   │   ├── voice.py         # Voice call initiation + Twilio webhooks
│   │   │   └── info.py          # Office info + doctor listing
│   │   └── services/
│   │       ├── ai_engine.py     # OpenAI GPT-4o wrapper with function calling
│   │       ├── doctor_matcher.py # Semantic specialty matching
│   │       ├── scheduling.py    # Slot management + booking
│   │       ├── email_service.py # SendGrid email notifications
│   │       ├── sms_service.py   # Twilio SMS notifications
│   │       └── voice_service.py # Twilio Voice call management
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app layout
│   │   ├── api/client.js        # API client
│   │   └── components/
│   │       ├── ChatWindow.jsx   # Chat interface + quick actions
│   │       ├── MessageBubble.jsx # Message rendering + appointment cards
│   │       ├── TypingIndicator.jsx
│   │       ├── SlotPicker.jsx   # Time slot selection UI
│   │       └── VoiceCallModal.jsx # Phone call handoff modal
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔒 Safety & Compliance

- AI **never provides medical advice**, diagnoses, or treatment plans
- All responses include appropriate disclaimers
- Patient data stored locally in SQLite (production: use encrypted DB)
- SMS requires explicit opt-in
- HIPAA considerations noted for production deployment

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

# Kyron_Medical_App
