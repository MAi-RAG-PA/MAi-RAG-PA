## Run it with Python 3:
#python3 audit_react_project.py
#It will generate a cleanup_report.json file with detailed info about duplicates and unused components.
#Use the report to clean up your project by removing or consolidating files.

"""
File: audit_react_project.py
Location: ./src (set PROJECT_ROOT below)
Description:
  This script audits a React project source directory for:
  - Duplicate and unused React components (based on export/import analysis)
  - ESLint issues (syntax, style, errors)
  - Prettier formatting issues
  - Duplicate files (using fdupes)
  - Unused dependencies/files (using depcheck)

Usage:
  python3 audit_react_project.py

Requirements:
  - Node.js installed with eslint, prettier, depcheck globally or locally in your project
  - fdupes installed on your system (Linux/macOS)
"""

import os
import re
import json
import subprocess
from collections import defaultdict

# === Configuration ===
PROJECT_ROOT = './frontend/src'  # Path to your React source directory
COMPONENTS_DIR = './frontend/src/components'
KEYWORDS = ['reminder', 'schedule', 'planner', 'todo', 'calendar', 'event']

# Regex Patterns for component detection
COMPONENT_DEF_PATTERNS = [
    re.compile(r'export\s+default\s+(?:function\s+)?([A-Z][A-Za-z0-9_]+)'),
    re.compile(r'export\s+const\s+([A-Z][A-Za-z0-9_]+)\s*=\s*(?:\$\$[^)]*\$\$|[A-Za-z0-9_]+)\s*=>'),
    re.compile(r'export\s+function\s+([A-Z][A-Za-z0-9_]+)')
]

IMPORT_PATTERN = re.compile(r'import\s+.*?\b([A-Z][A-Za-z0-9_]+)\b.*?from')

# === Helper Functions ===

def run_command(command, cwd=None):
    """Run a shell command and return stdout, stderr, and return code."""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, check=False)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def parse_eslint_output(eslint_json):
    """Parse ESLint JSON output to count errors and warnings."""
    total_errors = 0
    total_warnings = 0
    files_with_issues = 0
    for file_report in eslint_json:
        if file_report.get('errorCount', 0) > 0 or file_report.get('warningCount', 0) > 0:
            files_with_issues += 1
        total_errors += file_report.get('errorCount', 0)
        total_warnings += file_report.get('warningCount', 0)
    return {
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'files_with_issues': files_with_issues
    }

def parse_prettier_output(prettier_stdout):
    """Parse Prettier output to count files needing formatting."""
    # Prettier outputs filenames line by line for files needing formatting
    files = [line.strip() for line in prettier_stdout.splitlines() if line.strip()]
    return {
        'files_needing_formatting': len(files),
        'files_list': files
    }

def parse_fdupes_output(fdupes_stdout):
    """Parse fdupes output to group duplicate files."""
    duplicates = []
    current_group = []
    for line in fdupes_stdout.splitlines():
        if line.strip() == '':
            if current_group:
                duplicates.append(current_group)
                current_group = []
        else:
            current_group.append(line.strip())
    if current_group:
        duplicates.append(current_group)
    return duplicates

def parse_depcheck_output(depcheck_stdout):
    """Parse depcheck JSON output."""
    try:
        depcheck_json = json.loads(depcheck_stdout)
        return depcheck_json
    except json.JSONDecodeError:
        return {}

# === Main Audit Function ===

def audit_project():
    all_ts_files = []
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(('.tsx', '.jsx', '.ts', '.js')):
                all_ts_files.append(os.path.join(root, file))

    related_files = []
    component_to_path = defaultdict(list)
    import_counts = defaultdict(int)

    # 1. Map Components and find Related Files
    for filepath in all_ts_files:
        is_related = any(k in filepath.lower() for k in KEYWORDS)
        if is_related and filepath.startswith(COMPONENTS_DIR):
            related_files.append(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            # Find component definitions (only in components dir)
            if filepath.startswith(COMPONENTS_DIR):
                for pattern in COMPONENT_DEF_PATTERNS:
                    matches = pattern.findall(content)
                    for match in matches:
                        component_to_path[match].append(filepath)

            # Count imports (across entire src)
            imports = IMPORT_PATTERN.findall(content)
            for imp in imports:
                import_counts[imp] += 1

    # 2. Identify duplicates and unused components
    duplicates = {name: paths for name, paths in component_to_path.items() if len(paths) > 1}
    unused_components = []
    for comp_name, paths in component_to_path.items():
        if import_counts[comp_name] == 0:
            unused_components.append({"component": comp_name, "path": paths[0]})

    # 3. Run ESLint
    print("Running ESLint...")
    eslint_cmd = f"npx eslint {PROJECT_ROOT} --ext .js,.jsx,.ts,.tsx -f json"
    eslint_stdout, eslint_stderr, eslint_code = run_command(eslint_cmd)
    eslint_report = []
    if eslint_code == 0 and eslint_stdout:
        try:
            eslint_report = json.loads(eslint_stdout)
        except json.JSONDecodeError:
            print("Warning: ESLint output JSON parse failed.")
    eslint_summary = parse_eslint_output(eslint_report)

    # 4. Run Prettier check
    print("Running Prettier check...")
    prettier_cmd = f"npx prettier --check \"{PROJECT_ROOT}/**/*.{'{js,jsx,ts,tsx,json,css,md}'}\""
    prettier_stdout, prettier_stderr, prettier_code = run_command(prettier_cmd)
    prettier_summary = parse_prettier_output(prettier_stdout) if prettier_code != 0 else {'files_needing_formatting': 0, 'files_list': []}

    # 5. Run fdupes to find duplicate files (Linux/macOS)
    print("Running fdupes for duplicate files...")
    fdupes_cmd = f"fdupes -r {PROJECT_ROOT}"
    fdupes_stdout, fdupes_stderr, fdupes_code = run_command(fdupes_cmd)
    duplicates_files = parse_fdupes_output(fdupes_stdout) if fdupes_code == 0 else []

    # 6. Run depcheck for unused dependencies and files
    print("Running depcheck...")
    depcheck_cmd = f"npx depcheck --json"
    depcheck_stdout, depcheck_stderr, depcheck_code = run_command(depcheck_cmd)
    depcheck_report = parse_depcheck_output(depcheck_stdout) if depcheck_code == 0 else {}

    # 7. Compile final report
    report = {
        "summary": {
            "total_files_scanned": len(all_ts_files),
            "related_files_found": len(related_files),
            "unique_components_defined": len(component_to_path),
            "eslint": eslint_summary,
            "prettier": prettier_summary,
            "duplicate_files_groups": len(duplicates_files),
            "depcheck": depcheck_report,
        },
        "duplicates_components": duplicates,
        "potentially_unused_components": unused_components,
        "related_files_list": related_files,
        "duplicate_files_groups": duplicates_files,
    }

    with open('cleanup_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("✅ Report generated: cleanup_report.json")
    print(f"⚠️ Found {len(duplicates)} duplicate component names.")
    print(f"🗑️ Found {len(unused_components)} potentially unused components.")
    print(f"🗂️ Found {len(duplicates_files)} groups of duplicate files.")
    if eslint_code != 0:
        print("⚠️ ESLint reported errors or failed to run.")
    if prettier_code != 0:
        print("⚠️ Prettier found files needing formatting.")
    if depcheck_code != 0:
        print("⚠️ Depcheck failed to run or returned errors.")

if __name__ == "__main__":
    audit_project()
