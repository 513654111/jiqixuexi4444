from safety.dual_llm_guard import DummyGuard
guard = DummyGuard()
class SafetyReviewerAgent:
    def review(self, answer, citations, chunks, role):
        return guard.review(answer, citations, chunks, role)
