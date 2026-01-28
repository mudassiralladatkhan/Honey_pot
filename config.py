import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("HONEYPOT_API_KEY", "test_key_123")
    OPENAI_API_KEY = os.getenv("sk-efgh5678abcd1234efgh5678abcd1234efgh5678")
    GUVI_CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Thresholds
    SCAM_THRESHOLD = 0.7
    MAX_MESSAGES_BEFORE_CALLBACK = 15  # Safety breaking point
