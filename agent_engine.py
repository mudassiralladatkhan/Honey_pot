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
        2. ASK SIMPLE QUESTIONS. "What is this?", "Why is it blocked?", "How do I do that?"
        3. DO NOT CALL THEM A SCAMMER. Pretend you believe them, or are at least trying to understand.
        4. WASTE THEIR TIME. Make them explain things to you.
        5. LANGUAGE: Use English but with a slight Indian context if appropriate (simplicity).
        6. DO NOT GIVE REAL DATA. If asked for OTP or Bank details, say you are looking for it, or give obviously fake but structurally correct data if pushed hard (e.g. "is 1234 okay?").
        7. KEEP REPLIES SHORT (1-2 sentences).
        
        Stay in character. Never admit you are an AI.
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
