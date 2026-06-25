#!/usr/bin/env python3
# MAi-RAG_analyze_audit.py
"""
Use the local LLM to analyze the audit report and provide recommendations.
"""
import json
import os
import sys
from pathlib import Path
from langchain_ollama import ChatOllama

PROJECT_ROOT = Path.home() / "MAi-RAG"
AUDIT_REPORT = PROJECT_ROOT / "MAi-RAG_audit_report.json"
ANALYSIS_OUTPUT = PROJECT_ROOT / "MAi-RAG_audit_analysis.md"

def get_best_available_model() -> str:
    """Detect best available model for analysis."""
    # Check environment variable first
    env_model = os.getenv("MAI_RAG_AUDIT_MODEL")
    if env_model:
        return env_model
    
    # Check command-line argument
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # Try to import from agent_core
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from app.agents.agent_core import get_default_model
        return get_default_model()
    except Exception:
        pass
    
    # Fallback priority list
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            
            # Prefer coding models
            for preferred in ["qwen2.5-coder:32b", "qwen3.6:35b-a3b", "qwen3.5:35b-a3b", 
                             "qwen2.5-coder:14b", "qwen2.5-coder:7b"]:
                if preferred in models:
                    return preferred
            
            # Return first non-embedding model
            for model in models:
                if "embed" not in model.lower():
                    return model
    except Exception:
        pass
    
    # Ultimate fallback
    return "qwen2.5-coder:7b"

def analyze_with_llm():
    """Send audit report to LLM for analysis."""
    if not AUDIT_REPORT.exists():
        print(f"❌ Audit report not found: {AUDIT_REPORT}")
        print("Run MAi-RAG_audit_codebase.py first.")
        sys.exit(1)
    
    with open(AUDIT_REPORT, 'r') as f:
        report = json.load(f)
    
    model_name = get_best_available_model()
    print(f"🤖 Using model: {model_name}")
    
    llm = ChatOllama(
        model=model_name,
        temperature=0.1,
        num_predict=8192
    )
    
    # Create prompt
    prompt = f"""You are a senior software architect reviewing a codebase audit report.

AUDIT REPORT SUMMARY:
- Total files: {report['summary']['total_files']}
- Total lines: {report['summary']['total_lines']}
- Total issues: {report['summary']['total_issues']}
- Issues by type: {json.dumps(report['summary']['by_type'], indent=2)}

TOP 10 FILES WITH MOST ISSUES:
{json.dumps(sorted([f for f in report['files'] if f.get('issues')], key=lambda x: len(x.get('issues', [])), reverse=True)[:10], indent=2)}

Please provide:
1. Critical issues that need immediate attention
2. Architectural inconsistencies or anti-patterns
3. Code organization improvements
4. Specific refactoring recommendations
5. Priority-ordered action plan

Be specific and actionable. Reference actual file paths and line numbers where possible.
"""
    
    print("🤖 Analyzing audit report with LLM...")
    response = llm.invoke(prompt)
    
    # Save analysis
    with open(ANALYSIS_OUTPUT, 'w') as f:
        f.write("# MAi-RAG Codebase Audit Analysis\n\n")
        f.write(f"Generated: {report['timestamp']}\n\n")
        f.write(response.content)
    
    print(f"✅ Analysis saved to: {ANALYSIS_OUTPUT}")

if __name__ == "__main__":
    analyze_with_llm()
