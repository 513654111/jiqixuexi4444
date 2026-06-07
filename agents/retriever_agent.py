from rag.retrieval import HybridRetriever
from .schemas import RetrievalResult
ret = HybridRetriever()
class RetrieverAgent:
    def retrieve(self, req):
        chunks = ret.hybrid_search(req.query, top_k=req.top_k)
        return RetrievalResult(correlation_id=req.correlation_id, chunks=chunks)
