import requests
import logging
from config import Config
from models import ExtractedIntelligence

def send_final_result(session_id: str, 
                     total_messages: int, 
                     intelligence: ExtractedIntelligence, 
                     agent_notes: str = "Scam detected and engaged."):
    """
    Sends the mandatory callback to GUVI.
    """
    url = Config.GUVI_CALLBACK_URL
    
    # Convert intelligence model to dict
    intel_dict = intelligence.model_dump()
    
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intel_dict,
        "agentNotes": agent_notes
    }
    
    try:
        logging.info(f"Sending Callback for {session_id} to {url}")
        # Only sending mock request if network is restricted, but code is real.
        # response = requests.post(url, json=payload, timeout=10)
        
        # For Hackathon: Uncomment the real request below.
        # Ensure the URL is reachable from where this runs.
        # Use Exception handling to prevent crashing.
        
        # Simulating success for now if network is down or URL is invalid in dev
        # But providing the real code:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"Callback SUCCESS for {session_id}")
            return True
        else:
            logging.error(f"Callback FAILED for {session_id}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Callback EXCEPTION for {session_id}: {e}")
        return False
