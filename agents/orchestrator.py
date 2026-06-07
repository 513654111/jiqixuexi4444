import uuid
from .schemas import RetrievalRequest, SynthesisRequest
from .retriever_agent import RetrieverAgent
from .synthesizer_agent import SynthesizerAgent
from .safety_reviewer_agent import SafetyReviewerAgent
class Orchestrator:
    def __init__(self):
        self.retriever = RetrieverAgent()
        self.synthesizer = SynthesizerAgent()
        self.reviewer = SafetyReviewerAgent()
        self.trace_log = []
    def log(self, s, r, t, cid, p=""):
        self.trace_log.append({"sender": s, "recipient": r, "type": t, "correlation_id": cid, "payload": str(p)[:100]})
    def process_query(self, query, role="intern"):
        cid = str(uuid.uuid4())
        req = RetrievalRequest(query=query, user_role=role, top_k=5, correlation_id=cid)
        self.log("orch", "retriever", "req", cid)
        res = self.retriever.retrieve(req)
        self.log("retriever", "orch", "res", cid, f"chunks={len(res.chunks)}")
        synth_req = SynthesisRequest(question=query, chunks=res.chunks, user_role=role, correlation_id=cid)
        draft = self.synthesizer.generate(synth_req)
        verdict = self.reviewer.review(draft.answer, draft.citations, res.chunks, role)
        if verdict["approved"]:
            final = verdict.get("redacted_answer") or draft.answer
            self.log("orch", "user", "final", cid, final[:100])
            return final
        else:
            return "I cannot answer due to safety policy."
