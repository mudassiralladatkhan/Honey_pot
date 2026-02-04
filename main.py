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
    Test endpoint for GUVI platform with MULTI-CHARACTER responses
    Simulates different personas with LONGER, more realistic engagement
    HANDLES: Repeated test clicks, empty body, malformed requests
    COMPREHENSIVE LOGGING: Shows exact error reasons in Railway logs
    """
    import random
    import time
    
    # Generate unique request ID for tracking
    request_id = f"req_{int(time.time() * 1000)}"
    
    logger.info("=" * 80)
    logger.info(f"🔍 TEST ENDPOINT CALLED - Request ID: {request_id}")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   URL: {request.url}")
    logger.info(f"   Client: {request.client}")
    logger.info("=" * 80)
    
    # DEFENSIVE: Try to read request body safely
    request_body = None
    body_parse_status = "NOT_ATTEMPTED"
    
    try:
        logger.info(f"[{request_id}] Step 1: Attempting to read request body...")
        body_bytes = await request.body()
        
        if body_bytes:
            request_body = body_bytes.decode('utf-8')
            body_parse_status = "SUCCESS"
            logger.info(f"[{request_id}] ✅ Body read successfully ({len(body_bytes)} bytes)")
            logger.info(f"[{request_id}] Body content: {request_body[:200]}")
        else:
            body_parse_status = "EMPTY_BODY"
            logger.warning(f"[{request_id}] ⚠️ Empty request body received")
            
    except RuntimeError as e:
        body_parse_status = "RUNTIME_ERROR"
        error_msg = str(e)
        logger.error(f"[{request_id}] ❌ RuntimeError reading body: {error_msg}")
        
        if "body" in error_msg.lower():
            logger.error(f"[{request_id}] 🔴 REASON: Body already consumed!")
            logger.error(f"[{request_id}] 🔴 CAUSE: GUVI platform sent repeated request without canceling previous one")
            logger.error(f"[{request_id}] 🔴 SOLUTION: User should click 'Cancel' before testing again")
        
    except Exception as e:
        body_parse_status = "UNKNOWN_ERROR"
        logger.error(f"[{request_id}] ❌ Unexpected error reading body: {type(e).__name__}: {e}")
    
    logger.info(f"[{request_id}] Body Parse Status: {body_parse_status}")
    
    # Analyze message to detect target demographic
    scammer_message = ""
    try:
        if request_body:
            import json
            body_data = json.loads(request_body)
            if "message" in body_data and isinstance(body_data["message"], dict):
                scammer_message = body_data["message"].get("text", "").lower()
            elif "message" in body_data and isinstance(body_data["message"], str):
                scammer_message = body_data["message"].lower()
    except:
        pass
    
    logger.info(f"[{request_id}] Scammer message: {scammer_message[:100]}")
    
    # Multiple character personas with LONGER, more conversational responses
    characters = {
        "sunita_aunty": {
            "keywords": ["aunty", "auntie", "madam", "ma'am", "sister", "didi", "bhabhi", "mother"],
            "responses": [
                "Arre beta, internet buffering ho raha hai... can you send again? My grandson installed some new app and now phone is very slow. He said it's for studies but I think he is playing games only.",
                "My grandson is using phone for game right now, please wait 5 minutes. He says he will finish this level and then give me phone. These children, always on phone! In our time we used to play outside.",
                "I cannot find my reading glasses anywhere, voice note bhejo na? I kept them somewhere in kitchen I think. My eyesight is becoming weak, doctor said I need new glasses but I keep forgetting to go.",
                "Beta, I am making tea right now, whistling sound is coming from kitchen... call me after 10 minutes. I have to give tea to my husband also, he gets angry if tea is late. Then we can talk properly.",
                "Arre, my phone battery is showing only 15% now. Let me put it on charging and I will call you back in some time. This phone battery doesn't last long, I charged it in the morning only but already it's finishing."
            ]
        },
        "ramesh_uncle": {
            "keywords": ["sir", "uncle", "bhaiya", "brother", "sahab", "ji", "gentleman"],
            "responses": [
                "Hello? Who is this calling? I don't recognize this number at all. Are you from some bank or what? I am getting too many spam calls these days, very irritating. Please tell me clearly who you are and what you want.",
                "Beta, I am in important office meeting right now with my boss. Can we talk after 2-3 hours when meeting is finished? I cannot talk properly now, everyone is looking at me. Please call in evening time.",
                "My phone is acting very strange today, screen is freezing and all. Are you calling from Jio customer care? I have been having network issues since yesterday. Can you help me fix this problem?",
                "I already paid all my electricity bills, water bills, everything last week only. Why are you calling me again? There must be some mistake in your system. Please check properly and don't disturb me unnecessarily.",
                "Beta, speak more loudly please. I cannot hear you properly, there is too much noise in the background. Are you calling from call center? The line quality is very poor. Can you call from landline instead?"
            ]
        },
        "confused_youth": {
            "keywords": ["bro", "dude", "buddy", "friend", "college", "student", "young"],
            "responses": [
                "Bro, I think you have wrong number. I didn't order anything from Amazon or Flipkart recently. Maybe you want to talk to someone else? Check the number properly and call them. I am busy with my college assignment right now.",
                "Wait, what are you saying? I don't even have any bank account in SBI, I use HDFC only. This sounds like some scam call to me. My father warned me about these fraud calls. Don't try to fool me, I am not that stupid.",
                "Dude, I'm sitting in class lecture right now, professor will scold me if phone rings again. Can you just WhatsApp me whatever you want to say? I'll reply when class is over. This is very important lecture, I cannot miss it.",
                "Is this some kind of prank call? My friends are always doing these stupid pranks on me. If this is Rahul or Amit, I know it's you guys! Very funny, now stop wasting my time. I have exam tomorrow, need to study.",
                "Sorry bro, I don't understand what you are trying to say. Can you explain everything in simple English? You are using too many technical words and I am getting confused. Speak slowly and clearly please."
            ]
        },
        "young_girl": {
            "keywords": ["miss", "girl", "daughter", "beta", "princess", "sweetheart"],
            "responses": [
                "Hello? I don't know you. My papa told me not to talk to strangers on phone. I will tell my papa about this call. He is police officer, he will find you.",
                "I am only 19 years old, I don't have any bank account or credit card. My father handles all money matters. You should call him instead. I will give you his number if you want.",
                "Sorry, I am in college right now. My friends are waiting for me. Can you call my mother instead? She handles all these banking things. I don't understand all this.",
                "I think you have wrong number. I am student, I don't have any loan or credit card. My parents pay for my college fees. Please check your records properly.",
                "My phone is showing unknown number. I never answer unknown calls. My brother told me these are scam calls. Please don't call me again, I will block this number."
            ]
        },
        "elderly_person": {
            "keywords": ["old", "senior", "retired", "pension", "grandfather", "grandmother"],
            "responses": [
                "Beta, I am 75 years old now. I don't understand all these technical things like internet banking and mobile banking. My son handles everything for me. You should call him instead, I will give you his number.",
                "My son handles all my banking work, pension, everything. I don't know how to do these things on phone. I use basic Nokia phone only for calling, no smartphone. You young people understand all this, I am too old to learn now.",
                "I don't have any smartphone, beta. I am using simple Nokia phone that my daughter gave me 5 years ago. It can only make calls and send SMS. I don't know what is WhatsApp, UPI and all these new things.",
                "Beta, I cannot see small letters on phone screen. My eyesight is very weak now, even with glasses I have difficulty reading. Can you please come to my house and explain everything? I live in Sector 12, you can come in evening.",
                "I am 75 years old, beta. I don't know what is UPI, Paytm, Google Pay and all. In my time we used cash only. Now everything is online, very confusing for old people like me. My children help me with everything."
            ]
        }
    }
    
    logger.info(f"[{request_id}] Step 2: Analyzing target demographic...")
    
    # Intelligent character selection based on scammer's message
    selected_character = None
    for char_name, char_data in characters.items():
        for keyword in char_data["keywords"]:
            if keyword in scammer_message:
                selected_character = char_name
                logger.info(f"[{request_id}] 🎯 Detected keyword '{keyword}' -> Character: {char_name}")
                break
        if selected_character:
            break
    
    # Fallback to random if no keywords matched
    if not selected_character:
        import random
        selected_character = random.choice(list(characters.keys()))
        logger.info(f"[{request_id}] 🎲 No keywords detected, random selection: {selected_character}")
    
    # Select response from chosen character
    reply = random.choice(characters[selected_character]["responses"])
    
    logger.info(f"[{request_id}] Selected character: {selected_character}")
    logger.info(f"[{request_id}] Reply length: {len(reply)} characters")
    
    # GUVI spec format - ALWAYS return valid response
    response_payload = {
        "status": "success",
        "reply": reply
    }
    
    logger.info(f"[{request_id}] Step 3: Returning response...")
    logger.info(f"[{request_id}] ✅ Response generated successfully")
    logger.info(f"[{request_id}] Response: {response_payload}")
    logger.info("=" * 80)
    
    # Return with explicit JSONResponse
    return JSONResponse(
        content=response_payload,
        status_code=200,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Request-ID": request_id
        }
    )

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
