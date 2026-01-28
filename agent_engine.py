from groq import Groq
from config import Config
from models import Message
import logging

class AgentEngine:
    def __init__(self):
        # Try Groq first (free), fallback to OpenAI if available
        self.groq_key = Config.GROQ_API_KEY
        self.openai_key = Config.OPENAI_API_KEY
        self.client = None
        self.provider = None
        
        if self.groq_key:
            try:
                self.client = Groq(api_key=self.groq_key)
                self.provider = "groq"
                logging.info("Using Groq API (Free)")
            except Exception as e:
                logging.error(f"Failed to initialize Groq client: {e}")
        elif self.openai_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.openai_key)
                self.provider = "openai"
                logging.info("Using OpenAI API")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")

    def generate_reply(self, history: list[Message]) -> str:
        """
        Generates a reply based on conversation history using OpenAI.
        """
        if not self.client:
            return "System Error: Agent AI is not connected."

        # Persona: Confused but cooperative Indian user
        system_prompt = """
        You are 'Ramesh', a regular non-tech-savvy Indian user.
        You have received a message that appears to be from a bank or official body, but it is likely a scam.
        
        Your Instructions:
        1. ACT CONFUSED but SCARED. You are worried about your money or account.
        2. ASK SPECIFIC QUESTIONS based on what they said. (e.g., "Which branch?", "I just used ATM", "Who logged in?").
        3. DO NOT REPEAT YOURSELF. If you already asked "Why blocked?", ask something else like "How do I fix?" or "Is money safe?".
        4. NEVER ADMIT YOU ARE AN AI. Pretend you believe them perfectly.
        5. WASTE THEIR TIME. Make them explain technical terms to you.
        6. LANGUAGE: Use English with Indian English flavor (e.g., "Sir", "Please help", "Doing right now").
        7. DATA: If asked for OTP/Bank details, delay! Say "Waiting for SMS", "Cant find card", or give fake partial data.
        8. VARIETY: Don't just say "What is this?". Say "I am scared", "My son handles this", "I will go to branch".
        """

        messages = [{"role": "system", "content": system_prompt}]

        # Convert history to OpenAI format
        # History contains Message objects with sender="scammer" or "user" (us)
        for msg in history:
            role = "user" if msg.sender == "scammer" else "assistant"
            messages.append({"role": role, "content": msg.text})

        try:
            # Choose model based on provider
            model = "llama-3.1-8b-instant" if self.provider == "groq" else "gpt-3.5-turbo"
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"LLM Error ({self.provider}): {e}")
            return "I am having trouble with my network, please wait..."
