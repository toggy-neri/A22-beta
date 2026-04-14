import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

RAG_COLLECTION_NAME = "knowledge_base"
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

class RAGService:
    def __init__(self, collection_name: str = RAG_COLLECTION_NAME):
        self.collection_name = collection_name
        
        print(f"[RAG] Loading embedding model: {EMBEDDING_MODEL_NAME}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print(f"[RAG] Embedding model loaded successfully")
        
        self._documents: List[str] = []
        self._embeddings: List[np.ndarray] = []
        self._metadatas: List[Dict] = []
        self._ids: List[str] = []
        
        print(f"[RAG] RAG service initialized (simple memory mode)")
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        return self.embedding_model.encode(texts, convert_to_numpy=True)
    
    def add_documents(
        self, 
        documents: List[str], 
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        if not documents:
            return 0
        
        if ids is None:
            existing_count = len(self._documents)
            ids = [f"doc_{existing_count + i}" for i in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]
        
        embeddings = self._get_embeddings(documents)
        
        for i, (doc, emb, meta, doc_id) in enumerate(zip(documents, embeddings, metadatas, ids)):
            self._documents.append(doc)
            self._embeddings.append(emb)
            self._metadatas.append(meta)
            self._ids.append(doc_id)
        
        print(f"[RAG] Added {len(documents)} documents, total: {len(self._documents)}")
        return len(documents)
    
    def add_document(self, document: str, metadata: Optional[Dict] = None, doc_id: Optional[str] = None) -> str:
        if doc_id is None:
            doc_id = f"doc_{len(self._documents)}"
        
        if metadata is None:
            metadata = {"source": "unknown"}
        
        self.add_documents([document], [metadata], [doc_id])
        return doc_id
    
    def query(
        self, 
        query_text: str, 
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        if not self._documents:
            return {
                "query": query_text,
                "documents": [],
                "metadatas": [],
                "distances": [],
            }
        
        query_embedding = self._get_embeddings([query_text])[0]
        
        similarities = []
        for emb in self._embeddings:
            sim = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            similarities.append(sim)
        
        similarities = np.array(similarities)
        top_indices = np.argsort(similarities)[::-1][:n_results]
        
        documents = [self._documents[i] for i in top_indices]
        metadatas = [self._metadatas[i] for i in top_indices]
        distances = [1 - similarities[i] for i in top_indices]
        
        return {
            "query": query_text,
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
        }
    
    def get_context_for_query(self, query_text: str, n_results: int = 3, max_tokens: int = 1000) -> str:
        results = self.query(query_text, n_results)
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 2
        
        for i, doc in enumerate(results["documents"]):
            if total_chars + len(doc) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(f"[参考资料{i+1}]: {doc[:remaining]}...")
                break
            context_parts.append(f"[参考资料{i+1}]: {doc}")
            total_chars += len(doc)
        
        return "\n\n".join(context_parts)
    
    def delete_document(self, doc_id: str) -> bool:
        try:
            if doc_id in self._ids:
                idx = self._ids.index(doc_id)
                self._documents.pop(idx)
                self._embeddings.pop(idx)
                self._metadatas.pop(idx)
                self._ids.pop(idx)
                print(f"[RAG] Deleted document: {doc_id}")
                return True
            return False
        except Exception as e:
            print(f"[RAG] Delete error: {e}")
            return False
    
    def clear_collection(self):
        self._documents.clear()
        self._embeddings.clear()
        self._metadatas.clear()
        self._ids.clear()
        print(f"[RAG] Collection cleared")
    
    def get_document_count(self) -> int:
        return len(self._documents)
    
    def list_documents(self, limit: int = 100) -> List[Dict]:
        documents = []
        for i in range(min(limit, len(self._documents))):
            documents.append({
                "id": self._ids[i],
                "content": self._documents[i],
                "metadata": self._metadatas[i]
            })
        return documents


_rag_service_instance: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance


def query_knowledge_base(query_text: str, n_results: int = 3) -> str:
    rag = get_rag_service()
    return rag.get_context_for_query(query_text, n_results)


if __name__ == "__main__":
    rag = RAGService()
    
    test_docs = [
        "心理健康是指个体在心理、情感和行为方面的良好状态。",
        "焦虑是一种常见的情绪反应，适度的焦虑可以帮助我们应对挑战。",
        "抑郁症是一种常见的心理障碍，表现为持续的情绪低落和兴趣减退。",
    ]
    
    rag.add_documents(test_docs)
    
    query = "什么是心理健康？"
    context = rag.get_context_for_query(query)
    print(f"\n查询: {query}")
    print(f"上下文:\n{context}")
