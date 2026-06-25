#!/usr/bin/env python3
# ~/MAi-RAG/runtime_audit.py
"""
Finds runtime integration bugs that static analysis misses.
"""
import re
from pathlib import Path

PROJECT_ROOT = Path.home() / "MAi-RAG"

def find_runtime_bugs():
    issues = []
    
    # 1. Check for missing endpoint handlers (405 errors)
    main_py = (PROJECT_ROOT / "app" / "main.py").read_text()
    get_endpoints = set(re.findall(r'@app\.get\("([^"]+)"\)', main_py))
    post_endpoints = set(re.findall(r'@app\.post\("([^"]+)"\)', main_py))
    delete_endpoints = set(re.findall(r'@app\.delete\("([^"]+)"\)', main_py))
    
    # Check if frontend calls DELETE endpoints that don't exist
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        content = tsx_file.read_text()
        delete_calls = re.findall(r'apiClient\.delete\([\'"]([^\'"]+)[\'"]', content)
        for call in delete_calls:
            # Normalize endpoint pattern
            base = re.sub(r'\$\{[^}]+\}', '{id}', call)
            base = re.sub(r'/[a-f0-9-]+$', '/{id}', base)
            if not any(base.startswith(ep.rsplit('/', 1)[0]) for ep in delete_endpoints):
                issues.append(f"❌ Missing DELETE endpoint: {call} in {tsx_file.name}")
    
    # 2. Check for regex anchors that break filename extraction
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        content = tsx_file.read_text()
        if re.search(r'extractFilename.*\$\s*/i', content, re.DOTALL):
            issues.append(f"⚠️  Filename regex with $ anchor in {tsx_file.name}")
    
    # 3. Check for hook singleton violations
    hook_uses = {}
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        content = tsx_file.read_text()
        for hook in re.findall(r'use(\w+)\(', content):
            hook_uses.setdefault(hook, []).append(tsx_file.name)
    
    for hook, files in hook_uses.items():
        if hook.startswith("Event") or hook.startswith("Notification"):
            if len(files) > 1:
                issues.append(f"⚠️  Hook {hook} used in multiple files: {files}")
    
    # 4. Check for missing function definitions
    for tsx_file in (PROJECT_ROOT / "frontend" / "src").rglob("*.tsx"):
        content = tsx_file.read_text()
        # Find function calls
        calls = set(re.findall(r'\b(\w+)\s*\(', content))
        # Find function definitions
        defs = set(re.findall(r'(?:const|function)\s+(\w+)\s*(?:=|\()', content))
        defs.update(re.findall(r'(\w+)\s*:\s*(?:async\s+)?\(', content))
        
        # Check for handlers that are called but not defined
        handlers_called = {c for c in calls if c.startswith('handle')}
        handlers_defined = {d for d in defs if d.startswith('handle')}
        missing = handlers_called - handlers_defined - {'handleClick', 'handleSubmit', 'handleKeyDown'}
        for m in missing:
            issues.append(f"❌ Missing handler: {m}() in {tsx_file.name}")
    
    return issues

if __name__ == "__main__":
    print("🔍 Scanning for runtime integration bugs...")
    issues = find_runtime_bugs()
    print(f"\n📊 Found {len(issues)} issues:\n")
    for issue in issues:
        print(f"  {issue}")
