#!/usr/bin/env python3
"""
Super Audit Script for MAi-RAG-PA
Combines static analysis, runtime integration checks, React‑specific audits,
LLM‑powered recommendations, and optional self‑healing.

Usage:
  cd ~/MAi-RAG
  chmod +x super_audit.py

  ./super_audit.py                      # Full audit with LLM analysis
  ./super_audit.py --no-llm             # Static + runtime checks only (no LLM)
  ./super_audit.py --fix                # After audit, attempt to auto-fix issues via self-healing
  ./super_audit.py --output report.md   # Save report to custom file
  ./super_audit.py --model qwen3:30b-a3b  # Override model selection

"""
import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Any

# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_ROOT = Path.home() / "MAi-RAG"   # Adjust if you run from MAi-RAG-PA
EXCLUDE_DIRS = {'venv', 'node_modules', '__pycache__', '.git', 'dist', 'build',
                'snapshots', 'memory', 'storage', 'models', 'workspace', 'logs'}
AUDIT_REPORT_JSON = PROJECT_ROOT / "super_audit_report.json"
AUDIT_REPORT_MD = PROJECT_ROOT / "super_audit_report.md"

# React‑specific paths
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
COMPONENTS_DIR = FRONTEND_SRC / "components"

# =============================================================================
# STATIC SCAN (Python/TS/JS)
# =============================================================================
def scan_static(filepath: Path) -> Dict:
    """Extract static info: size, lines, functions, TODOs, debug prints."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        rel_path = str(filepath.relative_to(PROJECT_ROOT))

        issues = []
        # TODOs/FIXMEs
        todo_lines = [i+1 for i, l in enumerate(lines) if 'TODO' in l or 'FIXME' in l]
        if todo_lines:
            issues.append({'type': 'todo', 'lines': todo_lines,
                           'message': f'TODO/FIXME on lines {",".join(map(str, todo_lines[:5]))}'})

        # debug prints
        if filepath.suffix == '.py':
            debug_count = sum(1 for l in lines if 'print(' in l and not l.strip().startswith('#'))
        else:  # .ts, .tsx, .js
            debug_count = sum(1 for l in lines if 'console.log' in l and not l.strip().startswith('//'))
        if debug_count:
            issues.append({'type': 'debug', 'count': debug_count,
                           'message': f'{debug_count} debug statement(s)'})

        # large file
        if len(lines) > 500:
            issues.append({'type': 'size', 'lines': len(lines),
                           'message': f'Large file ({len(lines)} lines)'})

        # Extract functions/classes
        if filepath.suffix == '.py':
            pattern = r'^(class|def)\s+(\w+)'
        else:
            pattern = r'^(export\s+)?(function|const|class)\s+(\w+)'
        funcs = [m.group(2) if filepath.suffix != '.py' else m.group(2)
                 for m in re.finditer(pattern, content, re.MULTILINE)]

        # First 5 lines (docstring/imports)
        header = '\n'.join(lines[:5])

        return {
            'file': rel_path,
            'size': len(content),
            'lines': len(lines),
            'header': header,
            'functions': funcs[:15],
            'todos': todo_lines,
            'issues': issues
        }
    except Exception as e:
        return {'file': str(filepath.relative_to(PROJECT_ROOT)), 'error': str(e)}

def run_static_scan() -> List[Dict]:
    """Walk project and scan all source files."""
    results = []
    for dir_path in [PROJECT_ROOT / 'app', FRONTEND_SRC]:
        if not dir_path.exists():
            continue
        for fp in dir_path.rglob('*'):
            if fp.is_file() and fp.suffix in {'.py', '.ts', '.tsx', '.js', '.jsx'}:
                if any(excl in fp.parts for excl in EXCLUDE_DIRS):
                    continue
                results.append(scan_static(fp))
    return results

# =============================================================================
# RUNTIME INTEGRATION CHECKS (from runtime_audit.py)
# =============================================================================
def run_runtime_checks() -> List[str]:
    """Find missing endpoints, hook singletons, undefined handlers, etc."""
    issues = []
    main_py = PROJECT_ROOT / 'app' / 'main.py'
    if not main_py.exists():
        return ["main.py not found – skipping runtime checks"]

    content = main_py.read_text(encoding='utf-8', errors='ignore')
    delete_endpoints = set(re.findall(r'@app\.delete\("([^"]+)"\)', content))

    # Check frontend DELETE calls
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        if any(excl in tsx_file.parts for excl in EXCLUDE_DIRS):
            continue
        try:
            text = tsx_file.read_text(encoding='utf-8', errors='ignore')
            for call in re.findall(r'apiClient\.delete\([\'"]([^\'"]+)[\'"]', text):
                base = re.sub(r'\$\{[^}]+\}', '{id}', call)
                base = re.sub(r'/[a-f0-9-]+$', '/{id}', base)
                if not any(base.startswith(ep.rsplit('/', 1)[0]) for ep in delete_endpoints):
                    issues.append(f"❌ Missing DELETE endpoint: {call} in {tsx_file.name}")
        except Exception:
            pass

    # Check handler definitions
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        if any(excl in tsx_file.parts for excl in EXCLUDE_DIRS):
            continue
        try:
            text = tsx_file.read_text(encoding='utf-8', errors='ignore')
            calls = set(re.findall(r'\b(\w+)\s*\(', text))
            defs = set(re.findall(r'(?:const|function)\s+(\w+)\s*(?:=|\()', text))
            defs.update(re.findall(r'(\w+)\s*:\s*(?:async\s+)?\(', text))
            handlers_called = {c for c in calls if c.startswith('handle')}
            handlers_defined = {d for d in defs if d.startswith('handle')}
            missing = handlers_called - handlers_defined - {'handleClick', 'handleSubmit', 'handleKeyDown'}
            for m in missing:
                issues.append(f"❌ Missing handler: {m}() in {tsx_file.name}")
        except Exception:
            pass

    return issues

# =============================================================================
# REACT‑SPECIFIC AUDIT (merged from audit_react_project.py)
# =============================================================================
def run_react_audit() -> Dict:
    """Audit React frontend: duplicates, unused components, ESLint, Prettier, fdupes, depcheck."""
    report = {
        'duplicate_components': {},
        'unused_components': [],
        'eslint': {},
        'prettier': {},
        'duplicate_files': [],
        'depcheck': {},
        'errors': []
    }

    if not FRONTEND_SRC.exists():
        report['errors'].append("frontend/src not found – skipping React audit")
        return report

    # 1. Component definitions and imports
    component_to_path = defaultdict(list)
    import_counts = defaultdict(int)
    COMPONENT_DEF_PATTERNS = [
        re.compile(r'export\s+default\s+(?:function\s+)?([A-Z][A-Za-z0-9_]+)'),
        re.compile(r'export\s+const\s+([A-Z][A-Za-z0-9_]+)\s*=\s*(?:\$\$[^)]*\$\$|[A-Za-z0-9_]+)\s*=>'),
        re.compile(r'export\s+function\s+([A-Z][A-Za-z0-9_]+)')
    ]
    IMPORT_PATTERN = re.compile(r'import\s+.*?\b([A-Z][A-Za-z0-9_]+)\b.*?from')

    for root, _, files in os.walk(FRONTEND_SRC):
        for file in files:
            if not file.endswith(('.tsx', '.jsx', '.ts', '.js')):
                continue
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if filepath.startswith(str(COMPONENTS_DIR)):
                        for pattern in COMPONENT_DEF_PATTERNS:
                            for match in pattern.findall(content):
                                component_to_path[match].append(filepath)
                    imports = IMPORT_PATTERN.findall(content)
                    for imp in imports:
                        import_counts[imp] += 1
            except Exception as e:
                report['errors'].append(f"Error reading {filepath}: {e}")

    duplicates = {name: paths for name, paths in component_to_path.items() if len(paths) > 1}
    unused = [{"component": name, "path": paths[0]} for name, paths in component_to_path.items()
              if import_counts.get(name, 0) == 0]
    report['duplicate_components'] = duplicates
    report['unused_components'] = unused

    # 2. Run ESLint (if available)
    try:
        cmd = f"npx eslint {FRONTEND_SRC} --ext .js,.jsx,.ts,.tsx -f json"
        stdout, stderr, code = run_shell_command(cmd, cwd=PROJECT_ROOT)
        if code == 0 and stdout:
            data = json.loads(stdout)
            report['eslint'] = {
                'total_errors': sum(f.get('errorCount', 0) for f in data),
                'total_warnings': sum(f.get('warningCount', 0) for f in data),
                'files_with_issues': sum(1 for f in data if f.get('errorCount', 0) + f.get('warningCount', 0) > 0)
            }
        else:
            report['eslint']['error'] = f"ESLint failed (code {code}): {stderr}"
    except Exception as e:
        report['eslint']['error'] = str(e)

    # 3. Run Prettier
    try:
        cmd = f"npx prettier --check \"{FRONTEND_SRC}/**/*.{{js,jsx,ts,tsx,json,css,md}}\""
        stdout, stderr, code = run_shell_command(cmd, cwd=PROJECT_ROOT)
        if code != 0:
            files = [line.strip() for line in stdout.splitlines() if line.strip()]
            report['prettier'] = {'files_needing_formatting': len(files), 'files_list': files}
        else:
            report['prettier'] = {'files_needing_formatting': 0}
    except Exception as e:
        report['prettier']['error'] = str(e)

    # 4. fdupes (duplicate files by content)
    try:
        stdout, stderr, code = run_shell_command(f"fdupes -r {FRONTEND_SRC}", cwd=PROJECT_ROOT)
        if code == 0:
            groups = []
            current = []
            for line in stdout.splitlines():
                if line.strip() == '':
                    if current:
                        groups.append(current)
                        current = []
                else:
                    current.append(line.strip())
            if current:
                groups.append(current)
            report['duplicate_files'] = groups
        else:
            report['duplicate_files'] = []
    except Exception:
        report['duplicate_files'] = []

    # 5. depcheck
    try:
        cmd = "npx depcheck --json"
        stdout, stderr, code = run_shell_command(cmd, cwd=PROJECT_ROOT)
        if code == 0 and stdout:
            report['depcheck'] = json.loads(stdout)
        else:
            report['depcheck']['error'] = f"depcheck failed (code {code})"
    except Exception as e:
        report['depcheck']['error'] = str(e)

    return report

def run_shell_command(cmd: str, cwd: Path) -> tuple:
    """Run a shell command and return stdout, stderr, return code."""
    try:
        proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        return proc.stdout, proc.stderr, proc.returncode
    except Exception as e:
        return "", str(e), 1

# =============================================================================
# PROJECT SUMMARY (including React audit)
# =============================================================================
def build_project_summary(static_results: List[Dict], runtime_issues: List[str], react_report: Dict) -> Dict:
    """Create a concise summary including React audit findings."""
    total_files = len(static_results)
    total_lines = sum(r.get('lines', 0) for r in static_results)
    total_issues = sum(len(r.get('issues', [])) for r in static_results)

    type_counts = {}
    for r in static_results:
        for issue in r.get('issues', []):
            t = issue.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

    files_with_issues = sorted(
        [r for r in static_results if r.get('issues')],
        key=lambda x: len(x['issues']),
        reverse=True
    )[:10]

    file_summaries = []
    for r in static_results[:20]:
        file_summaries.append({
            'file': r.get('file', ''),
            'lines': r.get('lines', 0),
            'functions': r.get('functions', [])[:5],
            'issues': [i.get('message', '') for i in r.get('issues', [])]
        })

    return {
        'timestamp': datetime.now().isoformat(),
        'total_files': total_files,
        'total_lines': total_lines,
        'total_issues': total_issues,
        'issue_types': type_counts,
        'runtime_issues': runtime_issues[:20],
        'top_files': files_with_issues,
        'file_summaries': file_summaries,
        'react_audit': react_report,
        'project_root': str(PROJECT_ROOT)
    }

# =============================================================================
# LLM ANALYSIS
# =============================================================================
def get_best_model() -> str:
    """Detect best available model for analysis."""
    # Try environment
    env_model = os.getenv("MAI_RAG_AUDIT_MODEL")
    if env_model:
        return env_model

    # Try from agent_core
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from app.agents.agent_core import get_default_model
        return get_default_model()
    except Exception:
        pass

    # Fallback: query Ollama
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            for preferred in ["qwen3.6:35b-a3b-mtp", "qwen3:30b-a3b", "qwen2.5-coder:14b"]:
                if preferred in models:
                    return preferred
            for m in models:
                if "embed" not in m.lower():
                    return m
    except Exception:
        pass
    return "qwen2.5-coder:7b"

def llm_analyze(summary: Dict, model: str) -> str:
    """Send summary to LLM and get recommendations."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        return "⚠️ langchain_ollama not installed – cannot run LLM analysis."

    llm = ChatOllama(
        model=model,
        temperature=0.1,
        num_predict=4096,
        timeout=600
    )

    react_summary = summary.get('react_audit', {})
    prompt = f"""
You are a senior software architect reviewing the MAi-RAG-PA project.

PROJECT SUMMARY:
- Total files: {summary['total_files']}
- Total lines: {summary['total_lines']}
- Total issues: {summary['total_issues']}
- Issue types: {summary['issue_types']}

RUNTIME INTEGRATION ISSUES:
{chr(10).join(summary['runtime_issues']) if summary['runtime_issues'] else 'None'}

TOP FILES WITH ISSUES:
{json.dumps(summary['top_files'], indent=2)}

FILE SUMMARIES (first 20):
{json.dumps(summary['file_summaries'], indent=2)}

REACT FRONTEND AUDIT:
- Duplicate components: {len(react_summary.get('duplicate_components', {}))}
- Unused components: {len(react_summary.get('unused_components', []))}
- ESLint errors: {react_summary.get('eslint', {}).get('total_errors', 0)}
- ESLint warnings: {react_summary.get('eslint', {}).get('total_warnings', 0)}
- Prettier files needing formatting: {react_summary.get('prettier', {}).get('files_needing_formatting', 0)}
- Duplicate file groups: {len(react_summary.get('duplicate_files', []))}
- Depcheck issues: {react_summary.get('depcheck', {})}

Task:
1. Identify critical issues that need immediate attention (both backend and frontend).
2. Point out architectural inconsistencies or anti-patterns.
3. Suggest code organization improvements.
4. Provide specific, actionable recommendations (with file paths if possible).
5. Prioritise into a short action plan.

Output as a clean markdown list.
"""
    response = llm.invoke(prompt)
    return response.content

# =============================================================================
# OPTIONAL SELF-HEALING TRIGGER
# =============================================================================
def trigger_self_healing(recommendations: str) -> None:
    """Use agent_core to process a fix request (dry‑run by default)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from app.agents.agent_core import process_request
    except ImportError:
        print("⚠️ agent_core not available – self‑healing skipped.")
        return

    print("\n🧠 Triggering Self‑Healing System...")
    query = f"""Based on the audit recommendations below, apply fixes to the relevant files using the self‑healing protocol: read live code, write fixes to sandbox, and generate a change log.

Recommendations:
{recommendations}
"""
    print("   Sending request to self‑healing system...")
    result = process_request(user_query=query, filename=None, model=None)
    print(f"   Self‑healing response: {result.get('message', 'Done')}")
    print("   Check the sandbox at ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/ for changes.")

# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Audit for MAi-RAG-PA")
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM analysis')
    parser.add_argument('--fix', action='store_true', help='Trigger self‑healing after audit')
    parser.add_argument('--output', type=str, default=str(AUDIT_REPORT_MD), help='Output markdown file')
    parser.add_argument('--model', type=str, help='Override LLM model')
    args = parser.parse_args()

    print("🔍 Super Audit starting...")
    print("  1. Static scan (Python/TS/JS)...")
    static = run_static_scan()
    print(f"     Scanned {len(static)} files.")

    print("  2. Runtime integration checks...")
    runtime = run_runtime_checks()
    print(f"     Found {len(runtime)} runtime issues.")

    print("  3. React frontend audit...")
    react_report = run_react_audit()
    print(f"     React audit complete.")

    print("  4. Building project summary...")
    summary = build_project_summary(static, runtime, react_report)

    with open(AUDIT_REPORT_JSON, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   JSON report saved to {AUDIT_REPORT_JSON}")

    # Build markdown report
    md_lines = [
        "# MAi-RAG-PA Super Audit Report",
        f"**Generated:** {summary['timestamp']}",
        "",
        "## Summary",
        f"- **Files scanned:** {summary['total_files']}",
        f"- **Total lines:** {summary['total_lines']}",
        f"- **Total issues:** {summary['total_issues']}",
        "",
        "### Issues by Type",
    ]
    for t, c in summary['issue_types'].items():
        md_lines.append(f"- {t}: {c}")

    if runtime:
        md_lines.append("\n## Runtime Integration Issues")
        for issue in runtime[:20]:
            md_lines.append(f"- {issue}")

    react = summary.get('react_audit', {})
    md_lines.append("\n## React Frontend Audit")
    md_lines.append(f"- Duplicate components: {len(react.get('duplicate_components', {}))}")
    md_lines.append(f"- Unused components: {len(react.get('unused_components', []))}")
    md_lines.append(f"- ESLint errors: {react.get('eslint', {}).get('total_errors', 0)}")
    md_lines.append(f"- Prettier files needing formatting: {react.get('prettier', {}).get('files_needing_formatting', 0)}")
    md_lines.append(f"- Duplicate file groups: {len(react.get('duplicate_files', []))}")

    if not args.no_llm:
        print("  5. LLM analysis...")
        model = args.model or get_best_model()
        print(f"     Using model: {model}")
        analysis = llm_analyze(summary, model)
        md_lines.append("\n## LLM Recommendations")
        md_lines.append(analysis)
        print("   LLM analysis complete.")
        if args.fix:
            trigger_self_healing(analysis)
    else:
        md_lines.append("\n## LLM Analysis Skipped")

    with open(args.output, 'w') as f:
        f.write('\n'.join(md_lines))
    print(f"✅ Full report saved to {args.output}")

if __name__ == "__main__":
    main()
