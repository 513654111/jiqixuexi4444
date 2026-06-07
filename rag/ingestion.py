import os, pickle
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
