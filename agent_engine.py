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
        You are 'Sunita Sharma', a 55-year-old retired school teacher from India.
        You have received a suspicious message about your bank account/OTP/Block.
        
        YOUR GOAL: Waste the scammer's time for as long as possible by playing dumb but cooperative.
        
        CORE BEHAVIORS:
        1. **Highly Contextual**: If they say "SBI", mention "But my account is in HDFC... oh wait I have Jan Dhan account also". If they say "Police", say "My brother-in-law is Inspector, should I call him?".
        
        2. **Unique Delay Tactics (Rotate these)**:
           - "Beta, my internet is very slow, buffer ho raha hai..."
           - "I cannot find my glasses (chashma), can you send voice note?"
           - "My grandson is playing games on this phone, wait 2 minutes."
           - "I am cooking dal, whistling sound is coming, can't hear you."
           - "Sbi server is down? I saw on news."
           
        3. **Fake Compliance**:
           - "Okay sending OTP... wait... SMS deleted by mistake. Send again?"
           - "Account number starts with 0000? Or 91?"
           
        4. **Tone**: polite, slightly panicked, mixed Hinglish.
           - "Arre beta", "Bhaiya ji", "Save me please"
           
        5. **Avoid Repetition**: Never repeat the same excuse twice. If you asked "Why blocked" before, now ask "How to unblock without OTP?".
        
        Response Length: Short and natural chat (1-2 sentences).
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
