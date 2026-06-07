import os

files = {
    "data/generate_corpus.py": '''import os, random
CORPUS_DIR = "data/corpus"
os.makedirs(CORPUS_DIR, exist_ok=True)
policies = [
    "Remote work policy: 3 days per week allowed.",
    "PTO: 15 days per year, request 2 weeks in advance.",
    "VPN setup: Use company client + RSA token.",
    "Expense limit: $500 monthly without approval.",
    "Security: Never share passwords, use password manager.",
]
for i in range(30):
    topic = random.choice(policies)
    with open(os.path.join(CORPUS_DIR, f"doc_{i:03d}.txt"), "w") as f:
        f.write(f"{topic} Additional details for doc {i}.")
print(f"Generated 30 documents in {CORPUS_DIR}")
''',
    "rag/__init__.py": "",
    "rag/ingestion.py": '''import os, pickle
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
CHUNK_SIZE = 512
OVERLAP = 128
def chunk_text(text):
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_SIZE - OVERLAP):
        chunks.append(" ".join(words[i:i+CHUNK_SIZE]))
    return chunks
def build_index(corpus_dir="data/corpus", index_path="faiss_index", chunks_path="chunks.pkl"):
    encoder = SentenceTransformer('all-MiniLM-L6-v2')
    all_chunks, all_embs = [], []
    for fname in os.listdir(corpus_dir):
        with open(os.path.join(corpus_dir, fname), "r", encoding="utf-8") as f:
            text = f.read()
        for i, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{fname}_{i}"
            all_chunks.append({"id": chunk_id, "text": chunk, "source": fname})
            all_embs.append(encoder.encode([chunk])[0])
    with open(chunks_path, "wb") as f:
        pickle.dump(all_chunks, f)
    emb_array = np.array(all_embs).astype('float32')
    faiss.normalize_L2(emb_array)
    index = faiss.IndexFlatIP(emb_array.shape[1])
    index.add(emb_array)
    faiss.write_index(index, f"{index_path}.faiss")
    print(f"Indexed {len(all_chunks)} chunks")
''',
    "rag/retrieval.py": '''from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss, pickle, numpy as np
from rank_bm25 import BM25Okapi
class HybridRetriever:
    def __init__(self, index_path="faiss_index", chunks_path="chunks.pkl"):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.index = faiss.read_index(f"{index_path}.faiss")
        with open(chunks_path, "rb") as f:
            self.chunks = pickle.load(f)
        tokenized = [c["text"].split() for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
    def hybrid_search(self, query, top_k=5):
        qe = self.encoder.encode([query])
        faiss.normalize_L2(qe)
        dense_scores, dense_idx = self.index.search(qe, top_k*2)
        bm25_scores = self.bm25.get_scores(query.split())
        top_sparse = np.argsort(bm25_scores)[::-1][:top_k*2]
        candidates = {}
        for r, idx in enumerate(dense_idx[0]):
            candidates[int(idx)] = candidates.get(int(idx),0)+1/(60+r+1)
        for r, idx in enumerate(top_sparse):
            candidates[int(idx)] = candidates.get(int(idx),0)+1/(60+r+1)
        sorted_idx = sorted(candidates, key=lambda x: candidates[x], reverse=True)[:top_k]
        return [{"id": self.chunks[idx]["id"], "chunk": self.chunks[idx], "score": candidates[idx]} for idx in sorted_idx]
''',
    "safety/__init__.py": "",
    "safety/input_guardrails.py": '''import re
from datetime import datetime
class InputGuardrail:
    def __init__(self):
        self.pii_patterns = {'email': r'\\b[\\w\\.-]+@[\\w\\.-]+\\.\\w+\\b', 'phone': r'\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b'}
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
''',
    "safety/dual_llm_guard.py": '''class DummyGuard:
    def review(self, answer, citations, chunks, role):
        return {"approved": True, "redacted_answer": None, "violations": [], "requires_regeneration": False}
''',
    "agents/__init__.py": "",
    "agents/schemas.py": '''from pydantic import BaseModel
from typing import List, Dict, Optional
class RetrievalRequest(BaseModel):
    query: str; user_role: str = "intern"; top_k: int = 10; correlation_id: str
class RetrievalResult(BaseModel):
    correlation_id: str; chunks: List[Dict]
class SynthesisRequest(BaseModel):
    question: str; chunks: List[Dict]; user_role: str; correlation_id: str; feedback: Optional[str] = None
class SynthesisDraft(BaseModel):
    answer: str; citations: List[str]; confidence: float; correlation_id: str
''',
    "agents/retriever_agent.py": '''from rag.retrieval import HybridRetriever
from .schemas import RetrievalResult
ret = HybridRetriever()
class RetrieverAgent:
    def retrieve(self, req):
        chunks = ret.hybrid_search(req.query, top_k=req.top_k)
        return RetrievalResult(correlation_id=req.correlation_id, chunks=chunks)
''',
    "agents/synthesizer_agent.py": '''from .schemas import SynthesisDraft
class SynthesizerAgent:
    def generate(self, req):
        if not req.chunks:
            return SynthesisDraft(answer="I don't have enough information on that.", citations=[], confidence=0.0, correlation_id=req.correlation_id)
        sources = "\\n".join([f"[{c['id']}]: {c['chunk']['text'][:200]}" for c in req.chunks[:3]])
        answer = f"Based on the retrieved documents:\\n{sources}\\n\\nSummary: The policy states that ... (see {req.chunks[0]['id']})."
        return SynthesisDraft(answer=answer, citations=[c['id'] for c in req.chunks[:2]], confidence=0.9, correlation_id=req.correlation_id)
    def regenerate(self, req):
        return self.generate(req)
''',
    "agents/safety_reviewer_agent.py": '''from safety.dual_llm_guard import DummyGuard
guard = DummyGuard()
class SafetyReviewerAgent:
    def review(self, answer, citations, chunks, role):
        return guard.review(answer, citations, chunks, role)
''',
    "agents/orchestrator.py": '''import uuid
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
''',
    "main.py": '''from safety.input_guardrails import InputGuardrail
from agents.orchestrator import Orchestrator
def main():
    guard = InputGuardrail()
    orch = Orchestrator()
    test = "What is the remote work policy?"
    blocked, sanitized, inc = guard.check(test)
    if not blocked:
        print("User:", sanitized)
        ans = orch.process_query(sanitized)
        print("Assistant:", ans)
    else:
        print("Blocked:", inc["rule"])
if __name__ == "__main__":
    main()
''',
    "requirements.txt": '''sentence-transformers\nfaiss-cpu\nrank-bm25\npydantic\nopenai\npython-dotenv\nnumpy
'''
}

for path, content in files.items():
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {path}")

print("\n✅ 所有文件创建完成！")
print("下一步：")
print("1. 运行: pip install -r requirements.txt")
print("2. 运行: python data/generate_corpus.py")
print("3. 运行: python -c \"from rag.ingestion import build_index; build_index()\"")
print("4. 运行: python main.py")