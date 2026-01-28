# Agentic Honeypot for Scam Detection

## Problem Statement
We address the rising issue of online scams by creating an **Agentic Honeypot**. Unlike traditional firewalls that just block messages, our system engages the scammer using an AI persona to extract actionable intelligence (UPI IDs, Phone Numbers) which is then reported for takedown.

## Approach
1. **Scam Detection**: We use a hybrid rule-based and keyword-scoring engine to detect urgency and financial threats.
2. **Agentic Conversation**: Upon detection, control is passed to an AI Agent ("Ramesh", a confused user) powered by LLMs. This agent maintains a multi-turn conversation to waste the scammer's time and elicit payment details.
3. **Intelligence Extraction**: Regex and pattern matching logic run in real-time to capture UPIs and Accounts from the conversation history.
4. **Mandatory Callback**: Once sufficient intelligence is gathered, the system autonomously reports the findings to the GUVI evaluation URL.

## Tech Stack
- **Backend**: Python, FastAPI
- **AI/LLM**: OpenAI GPT-3.5/4
- **Intelligence**: Custom Regex Engine
- **Deployment**: Ready for Render/Vercel

## Unique Selling Point
Our solution correctly handles the full conversation lifecycle and implements the **Mandatory Final Callback** to close the feedback loop, ensuring the extracted intelligence is actionable.

## Ethics & Safety
The system uses simulated data and avoids impersonation or real financial interaction to ensure ethical AI usage. We prioritize privacy and do not store sensitive user data beyond the session scope.
