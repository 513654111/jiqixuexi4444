from .schemas import SynthesisDraft
class SynthesizerAgent:
    def generate(self, req):
        if not req.chunks:
            return SynthesisDraft(answer="I don't have enough information on that.", citations=[], confidence=0.0, correlation_id=req.correlation_id)
        sources = "\n".join([f"[{c['id']}]: {c['chunk']['text'][:200]}" for c in req.chunks[:3]])
        answer = f"Based on the retrieved documents:\n{sources}\n\nSummary: The policy states that ... (see {req.chunks[0]['id']})."
        return SynthesisDraft(answer=answer, citations=[c['id'] for c in req.chunks[:2]], confidence=0.9, correlation_id=req.correlation_id)
    def regenerate(self, req):
        return self.generate(req)
