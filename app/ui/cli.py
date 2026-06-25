from app.rag.retriever import Retriever
from app.rag.prompt_builder import build_prompt
from app.rag.generator import generate_answer

def run_cli(collection_name: str = "local_docs"):
    retriever = Retriever(collection_name)
    print("Welcome to MAi-RAG CLI! Type 'exit' to quit.")

    while True:
        query = input("\nYour question: ")
        if query.lower() in ["exit", "quit"]:
            break

        results = retriever.retrieve(query)
        prompt = build_prompt(query, results)
        answer = generate_answer(prompt)

        print(f"\nAnswer:\n{answer}")

if __name__ == "__main__":
    run_cli()
