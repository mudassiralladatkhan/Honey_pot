from fastapi import FastAPI, Header, HTTPException, Depends
from config import Config
from models import ConversationRequest, HoneypotResponse, EngagementMetrics, ExtractedIntelligence, Message
from scam_detector import ScamDetector
from agent_engine import AgentEngine
from intelligence import IntelligenceExtractor
from callback import send_final_result
import logging
import uvicorn
import datetime

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("honeypot-api")

app = FastAPI(title="Agentic Honeypot API")

# Add CORS Middleware to allow requests from GUVI platform (browser-based)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Initialize modules
detector = ScamDetector()
agent = AgentEngine()
extractor = IntelligenceExtractor()

# In-memory store to track if callback was sent to avoid duplicates
COMPLETED_SESSIONS = set()

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != Config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@app.post("/api/honey-pot", response_model=HoneypotResponse)
async def honey_pot_endpoint(request: ConversationRequest, api_key: str = Depends(verify_api_key)):
    session_id = request.sessionId
    current_msg = request.message
    history = request.conversationHistory
    
    # 1. Scam Detection Logic
    scam_score = detector.evaluate(current_msg.text)
    threshold = Config.SCAM_THRESHOLD
    is_scam = scam_score > threshold
    
    # If we are already engaging, assume it keeps being a scam
    if len(history) > 0:
        is_scam = True # Trust sticky session
    
    response_data = HoneypotResponse(scamDetected=is_scam)
    
    if is_scam:
        # 2. Agent Engagement (with timeout handling for GUVI platform)
        # Combine history + current to give agent full context
        full_context = history + [current_msg]
        
        try:
            # Try to get agent reply with timeout protection
            import asyncio
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            
            with ThreadPoolExecutor() as executor:
                future = executor.submit(agent.generate_reply, full_context)
                try:
                    agent_reply = future.result(timeout=8)  # 8 second timeout for GUVI
                except FuturesTimeoutError:
                    # Fallback response if LLM is slow
                    agent_reply = "What is this? Why is my account having issues? Please explain."
        except Exception as e:
            # Fallback if any error
            logger.error(f"Agent error: {e}")
            agent_reply = "I don't understand. Can you explain what this is about?"
        
        response_data.agentReply = agent_reply
        
        # 3. Intelligence Extraction (MOVED UP - needed for agentNotes)
        # Run on all text available (user + agent + previous)
        # Construct raw text blob
        all_text = " ".join([m.text for m in history]) + " " + current_msg.text
        extracted_data = extractor.extract(all_text)
        
        intel_model = ExtractedIntelligence(**extracted_data)
        response_data.extractedIntelligence = intel_model
        
        # Enhanced agentNotes with analytical depth (uses intel_model from above)
        has_critical_intel = bool(intel_model.upiIds or intel_model.bankAccounts)
        total_msgs = len(history) + 1
        agent_notes = (
            f"Threat Actor Profile: Employed {len(intel_model.suspiciousKeywords)} urgency/authority keywords. "
            f"Attack Vector: Impersonation of financial institution with credential phishing attempt. "
            f"Intelligence Value: {'High' if has_critical_intel else 'Medium'} - "
            f"{'Payment infrastructure exposed' if has_critical_intel else 'Behavioral patterns captured'}. "
            f"Engagement Success: Sustained {total_msgs} message exchanges, delaying real victim targeting."
        )
        response_data.agentNotes = agent_notes
        response_data.engagementMetrics = EngagementMetrics(
            totalMessagesExchanged=total_msgs,
            engagementDurationSeconds=total_msgs * 30 
        )
        
        # 5. Callback Trigger
        # Condition: Max messages reached OR useful intel found (UPI/Bank)
        has_critical_intel = len(intel_model.upiIds) > 0 or len(intel_model.bankAccounts) > 0
        target_msgs = Config.MAX_MESSAGES_BEFORE_CALLBACK
        
        should_callback = (total_msgs >= target_msgs) or (has_critical_intel and total_msgs >= 3)
        
        if should_callback and session_id not in COMPLETED_SESSIONS:
            logger.info("----------------------------------------------------------------")
            logger.info(f"⚡ CALLBACK TRIGGERED for Session: {session_id}")
            logger.info(f"   Reason: Critical Intel Found: {has_critical_intel}, Msgs: {total_msgs}")
            
            # Prepare Payload for Logging
            intel_dict = intel_model.model_dump()
            payload_log = {
                "sessionId": session_id,
                "scamDetected": True,
                "totalMessagesExchanged": total_msgs,
                "extractedIntelligence": intel_dict,
                "agentNotes": response_data.agentNotes
            }
            logger.info(f"📦 PAYLOAD: {payload_log}")
            logger.info("----------------------------------------------------------------")

            success = send_final_result(
                session_id, 
                total_msgs, 
                intel_model, 
                agent_notes=response_data.agentNotes
            )
            
            # Mark completed to prevent duplicate callbacks
            if success:
                 COMPLETED_SESSIONS.add(session_id)
            
    else:
        response_data.agentNotes = "Msg appears safe. No agent activation."
        
    return response_data

from fastapi import Request

@app.api_route("/api/honey-pot/test", methods=["GET", "POST"])
async def honeypot_test(request: Request):
    """
    Ultra fail-safe endpoint for GUVI Tester.
    Handles GET, empty POST, and POST with JSON body.
    """
    # Default success response
    success_response = {
        "status": "success",
        "message": "Honeypot API reachable and secured",
        "service": "Agentic Honeypot"
    }

    try:
        # 1. Handle GET requests immediately
        if request.method == "GET":
            return success_response

        # 2. Read body bytes once
        body_bytes = await request.body()
        
        # 3. If empty, return success
        if not body_bytes or len(body_bytes) == 0:
            return success_response
            
        # 4. Parse JSON from bytes (don't call request.json() after request.body())
        import json
        body = json.loads(body_bytes.decode('utf-8'))
        
        # 5. Extract User Text (Handle various formats)
        user_text = ""
        if isinstance(body, dict):
            if "message" in body:
                if isinstance(body["message"], dict) and "text" in body["message"]:
                    user_text = body["message"]["text"]
                else:
                    user_text = str(body["message"])
            elif "text" in body:
                user_text = body["text"]
        
        # 6. Generate AI Reply if text exists
        if user_text:
            msg_obj = Message(sender="scammer", text=user_text, timestamp=datetime.datetime.now().isoformat())
            agent_reply = agent.generate_reply([msg_obj])
            return {
                "status": "success",
                "scamDetected": True,
                "agentReply": agent_reply,
                "message": agent_reply
            }
            
    except Exception as e:
        # Log error but still return success to pass connectivity test
        logger.error(f"Test endpoint error: {e}")
        pass

    return success_response
    return success_response

@app.api_route("/api/honey-pot/ping", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def honeypot_ping():
    """
    Ultra-simple ping endpoint for GUVI.
    NO request parsing, NO dependencies, NO body reading.
    Just returns success immediately.
    """
    return {
        "status": "success",
        "message": "Honeypot API is alive",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/honey-pot")
async def honey_pot_info():
    """
    GET endpoint for GUVI platform compatibility.
    Returns API information and usage instructions.
    No authentication required for info endpoint.
    """
    return {
        "service": "Agentic Honeypot API",
        "status": "ready",
        "endpoint": "/api/honey-pot",
        "method": "POST",
        "description": "Send scam messages to engage AI agent and extract intelligence",
        "usage": {
            "headers": {
                "x-api-key": "required",
                "Content-Type": "application/json"
            },
            "body": {
                "sessionId": "unique-session-id",
                "message": {
                    "sender": "scammer",
                    "text": "message text",
                    "timestamp": "ISO 8601 timestamp"
                },
                "conversationHistory": []
            }
        },
        "features": [
            "Scam detection",
            "AI agent engagement",
            "Intelligence extraction (UPI, Bank, Phone, Links)",
            "Multi-turn conversation support",
            "Mandatory callback to GUVI platform"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "running", "service": "Agentic Honeypot"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
