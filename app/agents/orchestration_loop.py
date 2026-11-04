"""
Long-form document generation orchestration loop.
Maintains state across multiple LLM calls for coherent, multi-chunk writing.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.memory.sqlite_memory import SQLiteMemoryManager
from app.rag.retriever import Retriever
from app.agents.agent_core import _get_llm

logger = logging.getLogger(__name__)


class OrchestrationLoop:
    """Stateful, multi-chunk document generation with progress tracking."""

    def __init__(self, session_id: str, role_id: str):
        self.session_id = session_id
        self.role_id = role_id
        self.db = SQLiteMemoryManager()
        self.retriever = Retriever()

    def initialize_session(self, document_title: str, outline: List[Dict[str, Any]]):
        """Create a new generation session with outline."""
        with self.db.get_cursor() as cur:
            cur.execute("""
                INSERT INTO generation_sessions (id, role_id, document_title, total_sections)
                VALUES (?, ?, ?, ?)
            """, (self.session_id, self.role_id, document_title, len(outline)))

            for i, section in enumerate(outline, 1):
                cur.execute("""
                    INSERT INTO outline_manifest
                    (session_id, section_id, title, key_terms, tradition, word_target)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.session_id,
                    i,
                    section['title'],
                    json.dumps(section.get('key_terms', [])),
                    section.get('tradition', ''),
                    section.get('word_target', 3000)
                ))

    def write_next_chunk(self, model: str) -> Dict[str, Any]:
        """Generate the next chunk with full context."""

        # 1. Get current state
        with self.db.get_cursor() as cur:
            cur.execute("""
                SELECT current_section, chunks_written, words_written
                FROM generation_sessions WHERE id = ?
            """, (self.session_id,))
            state = cur.fetchone()

            if not state:
                raise ValueError(f"Session {self.session_id} not found")

            section_id = state[0]
            chunks_written = state[1]
            words_written = state[2]

            # 2. Get outline for this section
            cur.execute("""
                SELECT title, key_terms, tradition, word_target
                FROM outline_manifest WHERE session_id = ? AND section_id = ?
            """, (self.session_id, section_id))
            manifest = cur.fetchone()

            if not manifest:
                return {"status": "complete", "message": "All sections complete"}

            # 3. Retrieve context (with token budget)
            outline_context = self._get_outline_context(manifest[0], section_id)
            sources = self._get_source_materials(manifest[1], manifest[2])
            recent_chunks = self._get_recent_chunks(section_id, limit=3)
            progress_summary = self._get_progress_summary(section_id)

            # 4. Compose LLM prompt
            user_message = self._build_chunk_prompt(
                section_id=section_id,
                chunk_number=chunks_written + 1,
                outline=outline_context,
                sources=sources,
                recent_chunks=recent_chunks,
                progress_summary=progress_summary
            )

            # 5. Call LLM
            llm = _get_llm(model, num_ctx=8192, num_predict=2500)
            response = llm.invoke(user_message)

            # 6. Parse response
            chunk_text, progress_json = self._parse_response(response.content)

            # 7. Persist chunk
            chunk_id = f"written_{section_id}_chunk_{progress_json['chunk_number']}"
            cur.execute("""
                INSERT INTO written_chunks
                (id, session_id, section_id, chunk_number, text, summary,
                 words_count, new_terms_defined, claims_made)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                self.session_id,
                section_id,
                progress_json['chunk_number'],
                chunk_text,
                self._summarize_chunk(chunk_text),
                progress_json['words_in_chunk'],
                json.dumps(progress_json.get('new_terms_defined', [])),
                json.dumps(progress_json.get('claims_made', []))
            ))

            # 8. Update session state
            cur.execute("""
                UPDATE generation_sessions
                SET chunks_written = chunks_written + 1,
                    words_written = words_written + ?
                WHERE id = ?
            """, (progress_json['words_in_chunk'], self.session_id))

            # 9. Update terminology and claims
            for term in progress_json.get('new_terms_defined', []):
                cur.execute("""
                    INSERT OR IGNORE INTO terminology_ledger
                    (session_id, term, definition, section_id, first_used_chunk)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.session_id, term['term'], term.get('definition', ''),
                      section_id, chunk_id))

            for claim in progress_json.get('claims_made', []):
                cur.execute("""
                    INSERT INTO claims_ledger
                    (session_id, claim_text, claim_type, section_id, chunk_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.session_id, claim['text'], claim.get('type', 'factual'),
                      section_id, chunk_id))

            # 10. Update progress summary every 3 chunks
            if progress_json['chunk_number'] % 3 == 0:
                summary = self._summarize_section_progress(section_id)
                cur.execute("""
                    INSERT OR REPLACE INTO progress_summaries
                    (session_id, section_id, summary, key_arguments)
                    VALUES (?, ?, ?, ?)
                """, (self.session_id, section_id, summary['summary'],
                      json.dumps(summary['key_arguments'])))

            # 11. Check if section is complete
            if progress_json['words_in_section'] >= manifest[3] * 0.95:
                cur.execute("""
                    UPDATE outline_manifest SET status = 'complete'
                    WHERE session_id = ? AND section_id = ?
                """, (self.session_id, section_id))

                # Advance to next section
                cur.execute("""
                    UPDATE generation_sessions SET current_section = current_section + 1
                    WHERE id = ?
                """, (self.session_id,))

                return {
                    "status": "section_complete",
                    "chunk_text": chunk_text,
                    "section_id": section_id,
                    "next_section": section_id + 1
                }

            return {
                "status": "chunk_written",
                "chunk_text": chunk_text,
                "section_id": section_id,
                "chunk_number": progress_json['chunk_number'],
                "words_written": progress_json['words_in_section']
            }

    def _get_outline_context(self, title: str, section_id: int) -> str:
        """Retrieve outline chunk for this section."""
        try:
            # Instantiate retriever for the specific collection
            outline_retriever = Retriever(collection_name="outline_chunks")
            if not outline_retriever.qdrant_available:
                return title

            results = outline_retriever.retrieve(title, top_k=1)
            if results and isinstance(results[0], dict):
                # Handle both flat dicts and payload-wrapped dicts
                return results[0].get('text') or results[0].get('payload', {}).get('text', title)
        except Exception as e:
            logger.warning(f"Failed to retrieve outline context: {e}")
        return title

    def _get_source_materials(self, key_terms: str, tradition: str) -> List[Dict]:
        """Retrieve relevant source materials."""
        try:
            source_retriever = Retriever(collection_name="source_materials")
            if not source_retriever.qdrant_available:
                return []

            results = source_retriever.retrieve(key_terms, top_k=4)
            formatted = []
            for r in results[:4]:
                if isinstance(r, dict):
                    text = r.get('text') or r.get('payload', {}).get('text', '')
                    if text:
                        formatted.append({"text": text})
            return formatted
        except Exception as e:
            logger.warning(f"Failed to retrieve source materials: {e}")
            return []

    def _get_recent_chunks(self, section_id: int, limit: int = 3) -> List[Dict]:
        """Get last N chunks for continuity (from SQLite, not Qdrant, for perfect accuracy)."""
        with self.db.get_cursor() as cur:
            cur.execute("""
                SELECT text, summary FROM written_chunks
                WHERE session_id = ? AND section_id = ?
                ORDER BY chunk_number DESC LIMIT ?
            """, (self.session_id, section_id, limit))
            return [{"text": row[0], "summary": row[1]} for row in cur.fetchall()]

    def _get_progress_summary(self, section_id: int) -> Optional[Dict]:
        """Get compressed progress summary (100-200 words)."""
        with self.db.get_cursor() as cur:
            cur.execute("""
                SELECT summary, key_arguments FROM progress_summaries
                WHERE session_id = ? AND section_id = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (self.session_id, section_id))
            row = cur.fetchone()
            if row:
                return {"summary": row[0], "key_arguments": json.loads(row[1])}
        return None

    def _build_chunk_prompt(self, **kwargs) -> str:
        """Compose the LLM prompt with context budget management."""
        # Token budget: if context exceeds 3000 tokens, truncate
        prompt = f"""Write chunk {kwargs['chunk_number']} of section {kwargs['section_id']}.

OUTLINE FOR THIS SECTION:
{kwargs['outline']}

SOURCES AVAILABLE:
{self._format_sources(kwargs['sources'])}

PREVIOUS CHUNKS (for continuity):
{self._format_chunks(kwargs['recent_chunks'])}

SECTION SUMMARY SO FAR:
{kwargs['progress_summary']['summary'] if kwargs['progress_summary'] else 'None yet'}

KEY ARGUMENTS ALREADY MADE:
{json.dumps(kwargs['progress_summary']['key_arguments']) if kwargs['progress_summary'] else '[]'}

Write the next 800-1500 word chunk. Output the chunk text, then a JSON object with:
{{
  "chunk_number": {kwargs['chunk_number']},
  "words_in_chunk": <number>,
  "words_in_section": <total>,
  "new_terms_defined": [{{"term": "...", "definition": "..."}}],
  "claims_made": [{{"text": "...", "type": "factual|interpretive|speculative"}}]
}}
"""
        return prompt

    def _format_sources(self, sources: List[Dict]) -> str:
        """Format sources for prompt (truncate if too long)."""
        formatted = []
        total_tokens = 0
        for src in sources:
            text = src.get('text', '')
            tokens = len(text.split())
            if total_tokens + tokens > 1500:  # Budget
                break
            formatted.append(text)
            total_tokens += tokens
        return "\n\n---\n\n".join(formatted)

    def _format_chunks(self, chunks: List[Dict]) -> str:
        """Format recent chunks for continuity."""
        return "\n\n---\n\n".join([c['text'] for c in chunks])

    def _parse_response(self, response_text: str) -> tuple:
        """Parse LLM response into chunk text and progress JSON."""
        # Find the last complete JSON object
        json_start = response_text.rfind('{')
        if json_start == -1:
            raise ValueError("No JSON found in response")

        chunk_text = response_text[:json_start].strip()
        json_text = response_text[json_start:]

        # Find matching closing brace
        brace_count = 0
        json_end = 0
        for i, char in enumerate(json_text):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end == 0:
            raise ValueError("Incomplete JSON object")

        progress_json = json.loads(json_text[:json_end])
        return chunk_text, progress_json

    def _summarize_chunk(self, text: str) -> str:
        """Generate a 50-word summary of the chunk."""
        # Use a small model or simple extraction
        words = text.split()[:50]
        return ' '.join(words) + '...'

    def _summarize_section_progress(self, section_id: int) -> Dict:
        """Summarize all chunks in section so far."""
        with self.db.get_cursor() as cur:
            cur.execute("""
                SELECT text, claims_made FROM written_chunks
                WHERE session_id = ? AND section_id = ?
                ORDER BY chunk_number
            """, (self.session_id, section_id))
            chunks = cur.fetchall()

            # Combine all text and extract key arguments
            all_text = ' '.join([row[0] for row in chunks])
            all_claims = []
            for row in chunks:
                all_claims.extend(json.loads(row[1]))

            # Simple summary (first 200 words)
            summary = ' '.join(all_text.split()[:200]) + '...'

            return {
                "summary": summary,
                "key_arguments": [c['text'] for c in all_claims if c.get('type') == 'factual'][:10]
            }
