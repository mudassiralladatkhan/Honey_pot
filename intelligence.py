import re
from typing import List, Dict, Any

class IntelligenceExtractor:
    def extract(self, text: str) -> Dict[str, List[str]]:
        intelligence = {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": []
        }
        
        # 1. UPI IDs (e.g., something@okaxis, number@paytm)
        # Matches typical UPI formats
        upi_pattern = r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}"
        intelligence["upiIds"] = list(set(re.findall(upi_pattern, text)))
        
        # 2. Phone Numbers
        # Matches generic 10-digit patterns common in India, with optional +91
        phone_pattern = r"(?:\+91[\-\s]?)?[6-9]\d{9}\b" 
        # \b ensures we don't cut off longer numbers, but basic check is fine
        phones = re.findall(phone_pattern, text)
        intelligence["phoneNumbers"] = list(set([p.replace(" ", "").replace("-", "") for p in phones]))
        
        # 3. Phishing Links (http/https and www)
        url_pattern = r"(https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*|www\.[-\w]+\.[-\w]+[^\s]*)"
        intelligence["phishingLinks"] = list(set(re.findall(url_pattern, text)))
        
        # 4. Bank Account Numbers
        # Simple heuristic: 9 to 18 digits. To avoid phone numbers, check context or length.
        # Often preceded by 'customer id', 'account', 'ac no'
        acc_context_pattern = r"(?:account|ac|a/c|no|number)[\s\.:-]*([0-9]{9,18})"
        # Also just raw numbers that are clearly not phones (e.g. 11+ digits)
        raw_long_digits = r"\b\d{11,18}\b"
        
        context_matches = re.findall(acc_context_pattern, text, re.IGNORECASE)
        long_matches = re.findall(raw_long_digits, text)
        
        all_accounts = set(context_matches + long_matches)
        # Filter out valid phone numbers if they got caught (though phones are usually 10)
        intelligence["bankAccounts"] = list(all_accounts)
        
        # 5. Suspicious Keywords
        keywords = ["urgent", "verify", "block", "kyc", "otp", "refund", "password", "pin", "cvv", "expire"]
        found_kws = [kw for kw in keywords if kw in text.lower()]
        intelligence["suspiciousKeywords"] = list(set(found_kws))
        
        return intelligence

    def merge(self, old_intel: Dict, new_intel: Dict) -> Dict:
        """Merge new intelligence into existing intelligence (no duplicates)"""
        merged = old_intel.copy()
        
        # Ensure all keys exist
        keys = ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"]
        for k in keys:
            if k not in merged: merged[k] = []
            if k in new_intel:
                existing = set(merged[k])
                new_items = set(new_intel[k])
                merged[k] = list(existing.union(new_items))
        return merged
