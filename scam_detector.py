import re

SCAM_KEYWORDS = [
    "urgent", "immediately", "block", "suspend", "kyc", "verify", "pan card", 
    "adhaar", "aadhar", "otp", "credit card", "debit card", "upi", "lottery", 
    "winner", "prize", "refund", "electricity", "bill", "disconnect", 
    "account blocked", "click link", "verify now"
]

class ScamDetector:
    def evaluate(self, message_text: str) -> float:
        """
        Returns a scam score between 0.0 and 1.0
        """
        text_lower = message_text.lower()
        score = 0.0
        
        # Keyword matching
        matched_keywords = [kw for kw in SCAM_KEYWORDS if kw in text_lower]
        if matched_keywords:
            # Base score for having keywords + boost for quantity
            score += 0.4 + (min(len(matched_keywords), 5) * 0.1)
        
        # Urgency patterns
        if re.search(r"today|now|24 hours|immediate|soon", text_lower):
            score += 0.2
            
        # Financial patterns
        if re.search(r"bank|account|rs\.|rupees|fund|transfer|payment", text_lower):
            score += 0.2
            
        return min(score, 1.0)
