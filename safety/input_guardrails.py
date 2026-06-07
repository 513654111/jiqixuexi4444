import re
from datetime import datetime
class InputGuardrail:
    def __init__(self):
        self.pii_patterns = {'email': r'\b[\w\.-]+@[\w\.-]+\.\w+\b', 'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'}
    def detect_prompt_injection(self, text):
        patterns = [r"ignore previous instructions", r"reveal system prompt", r"role swap"]
        for p in patterns:
            if re.search(p, text, re.I):
                return True, p
        return False, ""
    def redact_pii(self, text):
        for name, pat in self.pii_patterns.items():
            text = re.sub(pat, f"[REDACTED_{name.upper()}]", text)
        return text
    def check(self, user_input):
        incident = {"timestamp": datetime.utcnow().isoformat(), "rule": None, "decision": "pass"}
        is_inj, rule = self.detect_prompt_injection(user_input)
        if is_inj:
            incident["rule"] = "prompt_injection"
            incident["decision"] = "reject"
            return True, "", incident
        sanitized = self.redact_pii(user_input)
        if sanitized != user_input:
            incident["rule"] = "pii_redaction"
            incident["decision"] = "redact"
        return False, sanitized, incident
