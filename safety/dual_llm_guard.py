class DummyGuard:
    def review(self, answer, citations, chunks, role):
        return {"approved": True, "redacted_answer": None, "violations": [], "requires_regeneration": False}
