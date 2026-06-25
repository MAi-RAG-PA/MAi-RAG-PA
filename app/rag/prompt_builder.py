# ~/MAi-RAG/app/rag/prompt_builder.py

def build_prompt(query: str, retrieved_chunks: list) -> str:
    """
    Build a prompt by concatenating retrieved chunks and appending the user query.
    """
    context = "\n\n".join([point.payload.get("text", "") for point in retrieved_chunks])
    prompt = f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}\nAnswer:"
    return prompt
