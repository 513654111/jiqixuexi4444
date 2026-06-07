from sentence_transformers import SentenceTransformer, CrossEncoder
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
