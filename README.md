<div align="center">

# 🍯 Honey_pot

### Agentic AI Honeypot — Waste Scammers' Time, Extract Intelligence

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3-FF6600?style=for-the-badge)](https://groq.com)
[![Docker](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

<br/>

**An AI-powered honeypot that automatically engages phone/SMS scammers with realistic Indian personas, wastes their time, and extracts threat intelligence (UPI IDs, bank accounts, phishing links).**

*🏆 India AI Impact Buildathon Submission — Problem Statement 2*

[How It Works](#-how-it-works) · [API](#-api-endpoints) · [Deploy](#-deployment)

---

</div>

## 🎯 What is This?

This is an **agentic AI system** that:

1. **Detects** incoming scam messages (OTP fraud, bank impersonation, UPI phishing)
2. **Engages** the scammer with a realistic AI persona that plays dumb but cooperative
3. **Extracts** intelligence: UPI IDs, bank accounts, phone numbers, phishing links
4. **Wastes** the scammer's time with delay tactics, keeping them away from real victims
5. **Reports** extracted intelligence via callback for law enforcement/anti-fraud systems

---

## 🧠 How It Works

```
Scammer Message → Scam Detector (keyword scoring)
                      │
                      ├── Not a scam → "Message appears safe"
                      │
                      └── Scam detected → Agent Engine (Groq/LLaMA 3)
                                              │
                                              ├── Generate persona reply (waste time)
                                              ├── Intelligence Extractor (UPI, banks, links)
                                              └── Engagement Metrics tracking
                                                      │
                                                      └── Threshold reached → Callback with intel
```

---

## 🎭 AI Personas

The agent plays **Sunita Sharma**, a 55-year-old retired teacher from India. Core behaviors:

| Tactic | Example |
|--------|---------|
| 🤔 **Playing dumb** | "Beta, I don't understand what is OTP..." |
| ⏳ **Delay tactics** | "My internet is very slow, buffer ho raha hai..." |
| 🎭 **Fake compliance** | "Okay sending OTP... wait... SMS deleted by mistake" |
| 😰 **Mild panic** | "Arre beta, save me please, what is happening" |
| 🔄 **Misdirection** | "My account is in HDFC... oh wait I have Jan Dhan also" |

Additional personas rotate for the test endpoint: Ramesh Uncle, Confused Youth, Young Girl, Elderly Person — each with distinct speech patterns and demographics.

---

## 🔍 Intelligence Extraction

Automatically extracts from conversation text:

| Type | Pattern |
|------|---------|
| 💳 **UPI IDs** | `name@upi`, `name@paytm`, etc. |
| 🏦 **Bank Accounts** | Account numbers, IFSC codes |
| 🔗 **Phishing Links** | Suspicious URLs in messages |
| 📱 **Phone Numbers** | Indian mobile numbers |
| ⚠️ **Suspicious Keywords** | "block", "OTP", "verify", "suspend", etc. |

---

## 📡 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/honey-pot` | Main honeypot — analyze message, engage scammer |
| `GET/POST` | `/api/honey-pot/test` | Quick test — returns persona reply |
| `GET/POST` | `/api/honey-pot/ping` | Health check |
| `GET` | `/api/honey-pot` | API info |
| `GET` | `/health` | Service health |

### Request Format

```json
{
  "sessionId": "session-123",
  "message": {
    "sender": "scammer",
    "text": "Your SBI account is blocked. Send OTP to verify.",
    "timestamp": "2026-01-15T10:30:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "sms",
    "language": "en"
  }
}
```

### Response Format

```json
{
  "status": "success",
  "scamDetected": true,
  "agentReply": "Arre beta, my account blocked? But I just went to bank yesterday...",
  "engagementMetrics": {
    "totalMessagesExchanged": 5,
    "engagementDurationSeconds": 150
  },
  "extractedIntelligence": {
    "bankAccounts": [],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://fake-sbi.com"],
    "phoneNumbers": ["+919876543210"],
    "suspiciousKeywords": ["blocked", "OTP", "verify"]
  },
  "agentNotes": "Threat Actor Profile: Employed 3 urgency/authority keywords..."
}
```

---

## 🏗️ Architecture

```
├── main.py              # FastAPI app, routes, CORS, exception handlers
├── agent_engine.py      # Groq/OpenAI LLM integration for persona replies
├── scam_detector.py     # Keyword-based scam scoring engine
├── intelligence.py      # Regex-based intel extraction (UPI, banks, links)
├── callback.py          # Final result reporting to external systems
├── models.py            # Pydantic models (request/response schemas)
├── config.py            # Environment configuration
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container deployment
├── nixpacks.toml        # Railway deployment config
└── test_production.py   # Production verification tests
```

---

## 🚀 Deployment

### Railway (Production)

```bash
# Already configured with nixpacks.toml
# Set environment variables in Railway dashboard:
# GROQ_API_KEY, API_KEY, CALLBACK_URL
```

### Local Development

```bash
git clone https://github.com/mudassiralladatkhan/Honey_pot.git
cd Honey_pot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add GROQ_API_KEY and other secrets

# Run
uvicorn main:app --reload --port 8000
```

---

## ⚙️ Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `GROQ_API_KEY` | Groq API for LLaMA 3 | Required |
| `OPENAI_API_KEY` | Fallback to OpenAI | Optional |
| `API_KEY` | API authentication | Optional |
| `CALLBACK_URL` | Intel reporting endpoint | Optional |
| `SCAM_THRESHOLD` | Detection sensitivity | 0.5 |
| `MAX_MESSAGES_BEFORE_CALLBACK` | Engagement limit | 10 |

---

## 🎯 Impact

- ⏱️ Each engagement wastes **3-5 minutes** of scammer time
- 🛡️ Prevents targeting of **real victims** during engagement
- 🔍 Extracts actionable intelligence for **anti-fraud teams**
- 📊 Tracks **engagement patterns** across sessions

---

<div align="center">

**Built with 🍯 by [Mudassir Alladatkhan](https://github.com/mudassiralladatkhan)**

*Every minute a scammer spends here is a minute they're not scamming someone's grandmother.*

</div>
