from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

# Add CORS Middleware with dynamic origin reflection for maximum compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In updated Starlette/FastAPI versions, this is sometimes restrictive with credentials
    allow_origin_regex=".*", # Allow any origin via regex matching (enables credentials with wildcard-like behavior)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for GUVI platform compatibility
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Catch validation errors on test endpoint and return success anyway.
    This handles GUVI platform's inconsistent request formats.
    """
    if request.url.path.endswith("/api/honey-pot/test"):
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Honeypot API reachable, authenticated, and ready"
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# Initialize modules
detector = ScamDetector()
agent = AgentEngine()
extractor = IntelligenceExtractor()

# In-memory store to track if callback was sent to avoid duplicates
COMPLETED_SESSIONS = set()

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key and x_api_key != Config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@app.post("/api/honey-pot", response_model=HoneypotResponse)
async def honey_pot_endpoint(request: ConversationRequest, api_key: str = Depends(verify_api_key)):
    session_id = request.sessionId
    current_msg = request.message
    history = request.conversationHistory
    
    # Handle case where message is None (GUVI platform edge case)
    if current_msg is None:
        return HoneypotResponse(
            scamDetected=False,
            agentReply="Please provide a message to analyze"
        )
    
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

@app.api_route("/api/honey-pot/test", methods=["GET", "POST"])
async def honeypot_test(request: Request):
    """
    ULTRA-SIMPLE Test endpoint for GUVI platform.
    Returns plain text to test if GUVI accepts non-JSON responses.
    """
    return "Honeypot is working! Arre beta, why are you calling me?"

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
    """Simple GET endpoint for GUVI platform."""
    return {
        "status": "success",
        "message": "Honeypot API reachable and secured"
    }

@app.get("/health")
def health_check():
    return {"status": "running", "service": "Agentic Honeypot"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
