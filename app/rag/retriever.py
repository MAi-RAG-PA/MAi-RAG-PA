# ~/MAi-RAG/app/rag/retriever.py
"""
RAG Retriever with Graceful Qdrant Degradation
Works with or without Qdrant running - logs warnings but never crashes
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class Retriever:
    """Simple semantic search retriever with graceful Qdrant degradation"""
    
    def __init__(self, collection_name: str = "local_docs"):
        self.collection_name = collection_name
        self.qdrant_available = False
        self.qdrant = None
        
        # Try to initialize Qdrant, but don't crash if it's not running
        try:
            from app.memory.qdrant_manager import QdrantMemoryManager
            self.qdrant = QdrantMemoryManager()
            # Test connection by listing collections
            self.qdrant.client.get_collections()
            self.qdrant_available = True
            logger.info("✅ Qdrant connection successful for Retriever")
        except ImportError as e:
            logger.warning(f"⚠️ QdrantMemoryManager not available: {e}")
            logger.warning("RAG features will be disabled")
        except Exception as e:
            logger.warning(f"⚠️ Qdrant not available for Retriever: {e}")
            logger.warning("RAG features will be disabled until Qdrant is running")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Simple semantic search with graceful degradation"""
        if not self.qdrant_available:
            logger.debug("Qdrant not available, returning empty results")
            return []
        
        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query=query,
                top_k=top_k
            )
            return results if results else []
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []


class AdvancedRetriever:
    """
    Advanced retriever with query expansion, deduplication, and graceful Qdrant degradation.
    This is the main RAG component used by the agent.
    """
    
    def __init__(self):
        self.qdrant_available = False
        self.qdrant = None
        self.available_collections = []
        
        # Try to initialize Qdrant, but don't crash if it's not running
        try:
            from app.memory.qdrant_manager import QdrantMemoryManager
            self.qdrant = QdrantMemoryManager()
            # Test connection and get available collections
            collections_response = self.qdrant.client.get_collections()
            self.available_collections = [c.name for c in collections_response.collections]
            self.qdrant_available = True
            logger.info(f"✅ Qdrant connection successful - {len(self.available_collections)} collections available")
            if self.available_collections:
                logger.info(f"   Collections: {', '.join(self.available_collections)}")
        except ImportError as e:
            logger.warning(f"⚠️ QdrantMemoryManager not available: {e}")
            logger.warning("RAG features will be disabled")
        except Exception as e:
            logger.warning(f"⚠️ Qdrant not available for AdvancedRetriever: {e}")
            logger.warning("RAG features will be disabled until Qdrant is running")
            logger.warning("To enable RAG: Start Qdrant and ensure it's accessible at localhost:6333")
        
    def expand_query(self, query: str) -> List[str]:
        """Query expansion with synonyms for better retrieval"""
        synonyms = {
            'document': ['file', 'paper', 'report'],
            'meeting': ['call', 'discussion', 'conference'],
            'project': ['task', 'work', 'assignment'],
            'code': ['program', 'script', 'implementation'],
            'error': ['bug', 'issue', 'problem'],
            'function': ['method', 'procedure', 'routine'],
        }
        expanded = [query]
        words = query.lower().split()
        for word in words:
            if word in synonyms:
                for syn in synonyms[word]:
                    if syn not in expanded:
                        expanded.append(query.replace(word, syn))
        return expanded[:3]  # Limit to 3 expansions max
    
    def get_best_collection(self) -> Optional[str]:
        """Get the best collection to search, prioritizing 'local_docs'"""
        if not self.available_collections:
            return None
        
        # Prefer 'local_docs' if it exists
        if 'local_docs' in self.available_collections:
            return 'local_docs'
        
        # Otherwise use the first available collection
        return self.available_collections[0] if self.available_collections else None
    
    def retrieve_advanced(self, 
                         query: str, 
                         top_k: int = 5,
                         filters: Dict[str, Any] = None,
                         min_score: float = 0.0) -> List[Dict]:
        """
        Hybrid search with query expansion and deduplication.
        Gracefully handles Qdrant being unavailable.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional metadata filters (not yet implemented in QdrantMemoryManager)
            min_score: Minimum similarity score threshold (0.0 = no filtering)
        
        Returns:
            List of result dictionaries with 'payload', 'score', 'id', etc.
        """
        if not self.qdrant_available:
            logger.debug("Qdrant not available, returning empty results")
            return []
        
        # Get the best collection to search
        collection = self.get_best_collection()
        if not collection:
            logger.warning("No collections available in Qdrant")
            return []
        
        # 1. Query expansion
        queries = self.expand_query(query)
        all_results = []
        
        for q in queries:
            try:
                # 2. Semantic search (QdrantMemoryManager handles embedding internally)
                results = self.qdrant.search(
                    collection_name=collection,
                    query=q,
                    top_k=top_k * 2  # Get more results for deduplication
                )
                
                if results:
                    # Tag each result with the query that found it
                    for result in results:
                        result['query_used'] = q
                        result['collection'] = collection
                        all_results.append(result)
                    
            except Exception as e:
                logger.warning(f"Query expansion search failed for '{q}': {e}")
                continue
        
        if not all_results:
            logger.debug(f"No results found for query: {query}")
            return []
        
        # 3. Filter by minimum score if specified
        if min_score > 0:
            all_results = [r for r in all_results if r.get('score', 0.0) >= min_score]
        
        # 4. Deduplicate by ID, keeping the highest-scoring result
        unique_results = []
        seen_ids = set()
        
        # Sort by score (highest first)
        sorted_results = sorted(
            all_results, 
            key=lambda x: x.get('score', 0.0), 
            reverse=True
        )
        
        for result in sorted_results:
            result_id = result.get('id')
            if result_id and result_id not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result_id)
                if len(unique_results) >= top_k:
                    break
        
        logger.info(f"RAG retrieval: {len(unique_results)} unique results from {collection}")
        return unique_results
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the RAG system"""
        return {
            "qdrant_available": self.qdrant_available,
            "available_collections": self.available_collections,
            "best_collection": self.get_best_collection() if self.qdrant_available else None
        }


# Keep backwards compatibility
def get_retriever(collection_name: str = "local_docs") -> Retriever:
    """Factory function for backwards compatibility"""
    return Retriever(collection_name)