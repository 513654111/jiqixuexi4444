from pydantic import BaseModel
from typing import List, Dict, Optional
class RetrievalRequest(BaseModel):
    query: str; user_role: str = "intern"; top_k: int = 10; correlation_id: str
class RetrievalResult(BaseModel):
    correlation_id: str; chunks: List[Dict]
class SynthesisRequest(BaseModel):
    question: str; chunks: List[Dict]; user_role: str; correlation_id: str; feedback: Optional[str] = None
class SynthesisDraft(BaseModel):
    answer: str; citations: List[str]; confidence: float; correlation_id: str
