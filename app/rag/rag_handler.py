# ~/MAi-RAG/app/rag/rag_handler.py
from rag_core import RAGCore

class RAGHandler:
    def __init__(self):
        self.core = RAGCore()

    def process_query(self, query, category="zen"):
        """Get RAG-augmented response for specific category"""
        context = self.core.query(query, category=category)
        context_str = "\n\n".join(context)

        system_prompt = f"""
        You are a professional assistant specializing in {category}.

        Use this context to answer truthfully. If the answer isn't in the context,
        say you don't know and recommend consulting the original texts.

        ---
        Context:
        {context_str}

        ---
        User: {query}
        """
        return {
            "system_prompt": system_prompt,
            "context": context,
            "query": query,
            "category": category
        }

    def add_knowledge(self, text, doc_id=None, category="zen"):
        """Add knowledge to specific category"""
        return self.core.add_document(text, doc_id, category=category)