#!/usr/bin/env python3
# MAi-RAG_audit_codebase.py
"""
MAi-RAG Codebase Auditor
Scans the project and generates a comprehensive report of issues, inconsistencies, and improvements.
"""
import os
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path.home() / "MAi-RAG"
AUDIT_REPORT = PROJECT_ROOT / "MAi-RAG_audit_report.json"

def scan_file(filepath: Path) -> dict:
    """Scan a single file for issues."""
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        issues = []
        
        # Check for common issues
        if 'TODO' in content or 'FIXME' in content:
            issues.append({
                'type': 'todo',
                'message': 'Contains TODO/FIXME comments',
                'lines': [i+1 for i, line in enumerate(lines) if 'TODO' in line or 'FIXME' in line]
            })
        
        if 'console.log' in content and filepath.suffix in ['.ts', '.tsx']:
            issues.append({
                'type': 'debug',
                'message': 'Contains console.log statements',
                'count': content.count('console.log')
            })
        
        if 'print(' in content and filepath.suffix == '.py':
            issues.append({
                'type': 'debug',
                'message': 'Contains print statements',
                'count': content.count('print(')
            })
        
        # Check file size
        if len(content) > 10000:
            issues.append({
                'type': 'size',
                'message': f'Large file ({len(content)} chars, {len(lines)} lines)',
                'recommendation': 'Consider splitting into smaller modules'
            })
        
        return {
            'file': str(filepath.relative_to(PROJECT_ROOT)),
            'size': len(content),
            'lines': len(lines),
            'issues': issues
        }
    except Exception as e:
        return {
            'file': str(filepath.relative_to(PROJECT_ROOT)),
            'error': str(e)
        }

def scan_project():
    """Scan entire project."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'project_root': str(PROJECT_ROOT),
        'files': [],
        'summary': {
            'total_files': 0,
            'total_lines': 0,
            'total_issues': 0,
            'by_type': {}
        }
    }
    
    # Scan directories
    scan_dirs = [
        PROJECT_ROOT / 'app',
        PROJECT_ROOT / 'frontend' / 'src',
    ]
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
            
        for filepath in scan_dir.rglob('*'):
            if filepath.is_file() and filepath.suffix in ['.py', '.ts', '.tsx', '.js', '.jsx']:
                # Skip node_modules, venv, etc
                if any(part in filepath.parts for part in ['node_modules', 'venv', '__pycache__', 'dist']):
                    continue
                
                file_report = scan_file(filepath)
                report['files'].append(file_report)
                report['summary']['total_files'] += 1
                report['summary']['total_lines'] += file_report.get('lines', 0)
                
                for issue in file_report.get('issues', []):
                    report['summary']['total_issues'] += 1
                    issue_type = issue['type']
                    report['summary']['by_type'][issue_type] = report['summary']['by_type'].get(issue_type, 0) + 1
    
    return report

def main():
    print("🔍 Scanning MAi-RAG codebase...")
    report = scan_project()
    
    # Save report
    with open(AUDIT_REPORT, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Audit complete. Report saved to: {AUDIT_REPORT}")
    print(f"\n📊 Summary:")
    print(f"  Files scanned: {report['summary']['total_files']}")
    print(f"  Total lines: {report['summary']['total_lines']}")
    print(f"  Issues found: {report['summary']['total_issues']}")
    
    if report['summary']['by_type']:
        print(f"\n  Issues by type:")
        for issue_type, count in report['summary']['by_type'].items():
            print(f"    {issue_type}: {count}")

if __name__ == "__main__":
    main()
