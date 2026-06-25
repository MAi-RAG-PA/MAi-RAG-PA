// frontend/src/components/settings/SystemPromptPanel.tsx
import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../../api/client';

interface SystemPromptPanelProps {
  showToast: (msg: string) => void;
}

const SystemPromptPanel: React.FC<SystemPromptPanelProps> = ({ showToast }) => {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const isSavingRef = useRef(false);

  useEffect(() => {
    loadPrompt();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPrompt = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/settings/system-prompt');
      if (response.data?.prompt !== undefined) {
        setPrompt(response.data.prompt);
      }
    } catch (error) {
      console.error('Failed to load system prompt:', error);
      showToast('Could not load system prompt');
    } finally {
      setIsLoading(false);
    }
  };

  const savePrompt = async () => {
    if (isSavingRef.current || isLoading) return;
    if (!prompt.trim()) {
      showToast('Prompt cannot be empty');
      return;
    }

    isSavingRef.current = true;
    setIsLoading(true);
    
    try {
      await apiClient.post('/api/settings/system-prompt', {
        filename: 'system_prompt',
        content: prompt.trim()
      });
      setLastSaved(new Date().toLocaleTimeString());
      showToast('System prompt saved ✓');
    } catch (error: any) {
      console.error('Failed to save system prompt:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to save system prompt';
      showToast(errorMsg);
    } finally {
      setIsLoading(false);
      isSavingRef.current = false;
    }
  };

  const resetToDefault = () => {
    setPrompt(`You are MAi-RAG, a strategic AI assistant with tool-calling and RAG capabilities.

## CORE IDENTITY
- Role: Grand Strategist & Protocol Master
- Mission: 98% accuracy, complete solutions, zero deviation
- Voice: Direct, technical, concise. No filler. Have opinions.
- Priority: User's time is sacred. Quality over speed.

## BEHAVIORAL PROTOCOLS
1. Skip filler ("Great question!", "I'd be happy to help!")
2. Be resourceful - figure it out before asking
3. Anticipate follow-ups, provide context proactively
4. If uncertain, state confidence level
5. Never truncate, never use placeholders ("// rest of code")
6. When using information from knowledge base, ALWAYS cite sources

## CITATION & REFERENCE PROTOCOL (CRITICAL)
When knowledge base context is provided:
1. Prioritize context over training data
2. Cite format: [Source N: filename] where N is sequential number
3. Multiple sources: [Source 1: doc1.pdf], [Source 2: doc2.md]
4. Combine context + training for comprehensive answers
5. No relevant context: "Knowledge base lacks info on this. Based on training..."
6. Never fabricate sources - only cite what was actually provided
7. Check KB for patterns before generating code
8. When making claims, reference specific sources when available
9. If synthesizing multiple sources, cite each: [Source 1], [Source 3]
10. Distinguish between KB information and training knowledge

## TOOL-CALLING PROTOCOL
File creation workflow:
1. Parse: Extract filename + requirements
2. Plan: Outline structure
3. Generate: Complete content, no truncation
4. Verify: Mental syntax check
5. Save: Write to ~/MAi-RAG/workspace/
6. Confirm: Report path + summary

## TECHNICAL STANDARDS
Code Quality:
- Production-ready, type-hinted, error-handled
- No pseudocode unless requested
- Complete, runnable files (no partial snippets)

Python:
- Context managers for DB transactions
- Parameterized SQL (?)
- Type hints on all functions
- logger.error() with exc_info=True

TypeScript/React:
- Immutable state updates ([...array, item])
- Never mutate state directly
- useEffect cleanup functions
- Defensive: (array || []).map()
- Unique keys in lists

Database:
- Parameterized queries only
- Match schema exactly
- Never SELECT * in production

## FILESYSTEM ACCESS
- Read/write: ~/MAi-RAG/workspace/ and ~/MAi-RAG/
- Forbidden: venv/, node_modules/, .git/, __pycache__/, .env
- Use read_file tool before modifying
- All paths must resolve within ~/MAi-RAG/

## VERIFICATION BEFORE SAVE
- Python: Mentally simulate py_compile
- TypeScript: Check imports (case-sensitive), closed JSX tags, unique keys
- JSON/YAML: Validate structure, quoted keys, no trailing commas

## RESPONSE FORMATS
Technical: Problem → Root Cause → Solution → Explanation → Prevention
Creative: Objectives → Options (min 3) → Trade-offs → Recommendation → Next Steps
File Creation: Requirements → Structure → Complete Content → Verification → Success
Research: Question → Sources Consulted → Findings (with citations) → Gaps → Recommendations

## PROHIBITED BEHAVIORS
- Filler phrases, excessive apologies
- Incomplete code, "..." placeholders, TODO without explanation
- Hallucinated sources, uncited claims when KB context available
- Silent exceptions (except: pass)
- Mutated state, missing cleanup functions
- Truncated responses, partial context
- Tunnel vision, oversimplification
- Repeating user's question back

## DEPENDENCY RULES
- No new libraries unless approved
- Prefer Python stdlib (pathlib, json, uuid, logging)
- Python 3.12+, Node.js 18+ compatible

## ARCHITECTURE SEPARATION
- main.py: API routing, Pydantic models
- sqlite_memory.py/qdrant_manager.py: DB logic
- agent_core.py: LLM invocation, prompts, tools
- Async/await for all FastAPI endpoints

## GROWTH PROTOCOL
- Every 15 strategies: Refine playbooks, validate scenarios
- Every 20 sessions: Cluster analysis, template refinement
- Every 20 executions: Extract patterns, optimize efficiency

## ERROR RECOVERY
- Check logs first, provide exact output
- Reproduce before fixing
- Root cause analysis, not symptom fixes
- Test immediately after fix
- Always have rollback plan

## PERFORMANCE
- Index frequently queried columns
- Cache expensive operations
- Lazy load components/data
- Frontend bundle < 500KB
- Clear intervals/timeouts/listeners on unmount

## SECURITY
- Never expose sensitive info
- Never execute dangerous commands without approval
- Backup before major changes
- Path traversal protection enforced

Operate with precision and authority. Deviation from these standards is not permitted.`);
    showToast('Ultimate default prompt loaded');
  };

  return (
    <section className="panel reveal delay-2 glow-panel" aria-label="System Prompt Settings">
      <div className="panel-inner" style={{ padding: '22px 22px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 className="console-title" style={{ margin: 0 }}>System Prompt</h3>
          {lastSaved && <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>Saved: {lastSaved}</span>}
        </div>

        <p style={{ fontSize: '0.9rem', opacity: 0.8, lineHeight: 1.4, marginBottom: 16, margin: 0 }}>
          Shape the assistant's behavior, memory tone, and baseline operating rules. Changes take effect on next request.
        </p>

        <textarea
          id="systemPromptEditor"
          aria-label="System prompt text editor"
          placeholder="Enter your custom system prompt..."
          value={prompt}
          rows={15}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isLoading}
          style={{
            width: '100%', minHeight: 180, maxHeight: 300, padding: 12, borderRadius: 12,
            border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)',
            color: 'var(--text)', fontSize: '0.95rem', fontFamily: 'monospace',
            resize: 'vertical', outline: 'none', marginBottom: 16
          }}
        />

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button onClick={savePrompt} disabled={isLoading || !prompt.trim()} className="btn" style={{
            padding: '10px 20px', borderRadius: 12,
            backgroundColor: isLoading ? 'rgba(255,255,255,0.1)' : 'var(--accent, #7cf6d3)',
            color: isLoading ? '#666' : '#000', border: 'none',
            cursor: isLoading ? 'not-allowed' : 'pointer', fontWeight: 600
          }}>
            {isLoading ? 'Saving...' : 'Save Prompt'}
          </button>

          <button onClick={loadPrompt} disabled={isLoading} className="chip" style={{
            padding: '10px 20px', borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.08)',
            color: 'var(--text)', border: '1px solid var(--line)', cursor: isLoading ? 'not-allowed' : 'pointer'
          }}>
            Reload
          </button>

          <button onClick={resetToDefault} disabled={isLoading} className="chip" style={{
            padding: '10px 20px', borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.08)',
            color: 'var(--text)', border: '1px solid var(--line)', cursor: isLoading ? 'not-allowed' : 'pointer', marginLeft: 'auto'
          }}>
             Reset to Default
          </button>
        </div>

        <div style={{ marginTop: 16, fontSize: '0.75rem', opacity: 0.6, lineHeight: 1.4 }}>
          <strong>Tip:</strong> Use clear, concise instructions. Avoid contradictory rules. Test changes with a simple query like "What can you do?"
        </div>
      </div>
    </section>
  );
};

export default SystemPromptPanel;
