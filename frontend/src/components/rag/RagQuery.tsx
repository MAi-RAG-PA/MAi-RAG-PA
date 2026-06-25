// MAi-RAG/frontend/src/components/rag/RagQuery.tsx

import React, { useState } from "react";
import axios from "axios";

const MODEL_OPTIONS = [
  { label: "Placeholder", value: "placeholder" },
  { label: "Local LLM", value: "local_llm" },
  { label: "Ollama", value: "ollama" },
];

const RagQuery: React.FC = () => {
  const [query, setQuery] = useState("");
  const [model, setModel] = useState("placeholder");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const response = await axios.post("/api/rag/query", {
        query,
        model_name: model,
        collection_name: "local_docs",
        top_k: 5,
      });
      setAnswer(response.data.answer);
    } catch (err) {
      setError("Failed to get answer from RAG API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <label>
          Select Model:
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <br />
        <label>
          Enter your query:
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            cols={50}
            required
          />
        </label>
        <br />
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Ask"}
        </button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {answer && (
        <div>
          <h3>Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
};

export default RagQuery;
