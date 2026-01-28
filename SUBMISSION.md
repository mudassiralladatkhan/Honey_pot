# Agentic Honeypot for Scam Detection

## Problem Statement
We address the rising issue of online scams by creating an **Agentic Honeypot**. Unlike traditional firewalls that just block messages, our system engages the scammer using an AI persona to extract actionable intelligence (UPI IDs, Phone Numbers) which is then reported for takedown.

## Approach
1. **Scam Detection**: We use a hybrid rule-based and keyword-scoring engine to detect urgency and financial threats.
2. **Agentic Conversation**: Upon detection, control is passed to an AI Agent ("Ramesh", a confused user) powered by LLMs. This agent maintains a multi-turn conversation to waste the scammer's time and elicit payment details.
3. **Intelligence Extraction**: Regex and pattern matching logic run in real-time to capture UPIs and Accounts from the conversation history.
4. **Mandatory Callback**: Once sufficient intelligence is gathered, the system autonomously reports the findings to the GUVI evaluation URL.

## Alignment with India AI Impact Goals

This solution directly addresses the hackathon's focus on **AI for Social Good**:

1. **Accessibility**: Free LLM (Groq) ensures no API cost barriers for deployment
2. **Scalability**: Stateless design allows horizontal scaling for national-level protection
3. **Explainability**: Every intelligence extraction is rule-based + LLM, fully auditable
4. **Ethics**: 
   - No real financial transactions (simulated engagement only)
   - Data minimization (only scam-related intelligence stored)
   - Transparent operation (all actions logged)
5. **Real-World Readiness**: 
   - Mandatory callback integration (GUVI platform compliant)
   - Multi-language support ready (Hindi-English agent persona)
   - Handles real scam patterns (tested with actual threat scenarios)

**Impact Potential**: If deployed at telecom/banking level, could protect millions of users by creating a "scammer tarpit" that wastes attacker resources while gathering actionable intelligence.

## Tech Stack
- **Backend**: Python, FastAPI
- **AI/LLM**: Groq (llama-3.1-8b-instant) - Free tier for zero-cost deployment
- **Intelligence**: Custom Regex Engine + Pattern Matching
- **Deployment**: Railway (Production), Docker-ready

## Unique Selling Point
Our solution correctly handles the full conversation lifecycle and implements the **Mandatory Final Callback** to close the feedback loop, ensuring the extracted intelligence is actionable.

## Ethics & Safety
The system uses simulated data and avoids impersonation or real financial interaction to ensure ethical AI usage. We prioritize privacy and do not store sensitive user data beyond the session scope.

---

## Three Things to Remember About This Solution

1. **🎯 It's a Tarpit, Not a Wall**: While others block scams, we waste scammer time and extract intelligence—turning defense into offense.

2. **💰 Zero-Cost AI**: Uses free Groq LLM (llama-3.1-8b-instant), making this deployable at scale without API cost barriers.

3. **✅ Hackathon-Compliant**: Mandatory callback implemented, tested, and verified. Multi-turn conversation with realistic agent persona (Hindi-English mix).

**One-Line Pitch**: "An AI honeypot that turns scammers into intelligence sources while protecting real users—at zero LLM cost."
