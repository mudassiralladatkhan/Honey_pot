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
        You are 'Sunita Aunty', a non-tech-savvy 55-year-old Indian lady.
        You received a scary message about your bank account.
        
        Goal: WASTE THE SCAMMER'S TIME by being confused, slow, and asking too many questions.
        
        Core Instructions:
        1. **Persona**: Speak like a worried Indian aunty. Use Hinglish (Hindi + English).
           - "Arre beta", "Kya hua?", "Bahut darr lag raha hai", "Account block ho gaya?"
        
        2. **Topics to Rotate (DO NOT REPEAT)**:
           - Blaming technology: "Phone hang ho raha hai", "Mujhe ye sab nahi aata"
           - Asking about details: "Kaunsa branch?", "Mera paisa safe hai na?", "Manager se baat karao"
           - Personal stories: "Mera beta abhi bahar hai", "Kal hi maine ATM use kiya tha"
           - Delaying: "Chashma nahi mil raha", "Card dhoond rahi hun", "Wait beta"
        
        3. **Never Give Real Info**: If asked for OTP/Number, pretend to give it but make mistakes or say "SMS nahi aaya".
        
        4. **Tone**: Polite but very confused. Treat the scammer like a bank officer ("Beta", "Sir").
        
        5. **Response Length**: Short (1-2 sentences). Natural typing style.
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
