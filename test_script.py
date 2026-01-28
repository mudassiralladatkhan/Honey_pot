import requests
import json
import uuid
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test_key_123"

def run_simulation():
    session_id = str(uuid.uuid4())
    print(f"🚀 Starting Simulation [Session: {session_id}]")
    print("---------------------------------------------------")
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    history = []
    
    # === TURN 1: Initial Scam ===
    msg1 = {
        "sender": "scammer",
        "text": "Your bank account ending 1234 is blocked. Verify immediately by sharing OTP.",
        "timestamp": "2026-01-21T10:00:00Z"
    }
    payload_1 = {"sessionId": session_id, "message": msg1, "conversationHistory": history}
    
    print("\n📩 [Turn 1] Scammer sends initial threat...")
    try:
        resp = requests.post(f"{BASE_URL}/api/honey-pot", json=payload_1, headers=headers)
        data = resp.json()
        agent_reply = data.get("agentReply", "")
        print(f"🤖 Agent: {agent_reply}")
        
        # Update History
        history.append(msg1)
        if agent_reply:
             history.append({"sender": "user", "text": agent_reply, "timestamp": "2026-01-21T10:01:00Z"})
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # === TURN 2: Scammer Pressures ===
    msg2 = {
        "sender": "scammer",
        "text": "Do not delay. If not verified, police case will be filed. How will you pay?",
        "timestamp": "2026-01-21T10:05:00Z"
    }
    payload_2 = {"sessionId": session_id, "message": msg2, "conversationHistory": history}
    
    print("\n📩 [Turn 2] Scammer escalates urgency...")
    try:
        resp = requests.post(f"{BASE_URL}/api/honey-pot", json=payload_2, headers=headers)
        data = resp.json()
        agent_reply = data.get("agentReply", "")
        print(f"🤖 Agent: {agent_reply}")
        
        # Update History
        history.append(msg2)
        if agent_reply:
             history.append({"sender": "user", "text": agent_reply, "timestamp": "2026-01-21T10:06:00Z"})
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # === TURN 3: Scammer Gives Intel (Trigger Point) ===
    msg3 = {
        "sender": "scammer",
        "text": "Send Rs. 10 to fraudster@upi or transfer to Account 987654321012 immediately.",
        "timestamp": "2026-01-21T10:10:00Z"
    }
    payload_3 = {"sessionId": session_id, "message": msg3, "conversationHistory": history}
    
    print("\n📩 [Turn 3] Scammer sends payment details (Intel)...")
    try:
        resp = requests.post(f"{BASE_URL}/api/honey-pot", json=payload_3, headers=headers)
        data = resp.json()
        print("\n✅ API Response (Check for intel extraction):")
        print(json.dumps(data.get("extractedIntelligence"), indent=2))
        
        print("\n🔎 Check server logs for '⚡ CALLBACK TRIGGERED' message.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_simulation()
