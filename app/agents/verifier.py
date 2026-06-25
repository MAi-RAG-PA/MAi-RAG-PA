# app/agents/verifier.py
import ast, json, re, csv, io
from pathlib import Path
from typing import Optional

class ContentVerifier:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def verify_python(self, content: str) -> dict:
        try:
            ast.parse(content)
            return {"valid": True, "message": "✓ Syntax OK"}
        except SyntaxError as e:
            return {"valid": False, "message": f"✗ SyntaxError: {e}"}

    def verify_json(self, content: str) -> dict:
        try:
            json.loads(content)
            return {"valid": True, "message": "✓ Valid JSON"}
        except json.JSONDecodeError as e:
            return {"valid": False, "message": f"✗ JSONError: {e}"}

    def verify_text_quality(self, content: str) -> dict:
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        
        # Paragraph structure check
        if len(content) > 500 and '\n\n' not in content:
            return {"valid": False, "message": "✗ Long text lacks paragraph breaks"}
        
        # Basic grammar heuristics (no external lib)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if lines and not lines[0][0].isupper() and not lines[0].startswith(('-', '*', '#')):
            return {"valid": False, "message": "✗ First line should start with capital or marker"}
        
        # Repetition/spam check
        if re.search(r'(.)\1{4,}', content):  # 5+ repeated chars
            return {"valid": False, "message": "✗ Excessive character repetition"}
        
        # Basic spelling: flag common typos (expandable)
        typos = {'teh': 'the', 'adn': 'and', 'recieve': 'receive'}
        for typo, correct in typos.items():
            if re.search(rf'\b{typo}\b', content, re.I):
                return {"valid": False, "message": f"✗ Possible typo: '{typo}' → '{correct}'"}
        
        return {"valid": True, "message": "✓ Text structure OK"}

    def verify_javascript(self, content: str) -> dict:
        """Basic JavaScript structure checks (no external parser)"""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        
        # Check for balanced braces/brackets/parens
        stack = []
        pairs = {'{': '}', '[': ']', '(': ')'}
        for char in content:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack or pairs[stack.pop()] != char:
                    return {"valid": False, "message": f"✗ Unbalanced bracket: {char}"}
        
        if stack:
            return {"valid": False, "message": f"✗ Unclosed bracket: {stack[-1]}"}
        
        # Basic syntax heuristics
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('//')]
        for line in lines:
            # Check for common JS syntax issues
            if re.match(r'^(function|const|let|var|class)\s+\w+\s*[=(\{]?', line):
                if not line.rstrip().endswith(('{', ';', ')', '}')) and '=' not in line:
                    return {"valid": False, "message": "✗ Possible missing semicolon or block"}
        
        return {"valid": True, "message": "✓ JavaScript structure OK"}

    def verify_yaml(self, content: str) -> dict:
        """YAML structure validation using safe load"""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        
        try:
            # Use safe_load to avoid code execution
            import yaml
            yaml.safe_load(content)
            return {"valid": True, "message": "✓ Valid YAML structure"}
        except yaml.YAMLError as e:
            return {"valid": False, "message": f"✗ YAML Error: {str(e)}"}
        except ImportError:
            # Fallback: basic structure checks if PyYAML not installed
            lines = content.split('\n')
            indent_stack = [0]
            for i, line in enumerate(lines, 1):
                if not line.strip() or line.strip().startswith('#'):
                    continue
                # Check indentation is consistent (2 or 4 spaces)
                indent = len(line) - len(line.lstrip())
                if indent % 2 != 0 and indent > 0:
                    return {"valid": False, "message": f"✗ Line {i}: Inconsistent indentation"}
            return {"valid": True, "message": "✓ Basic YAML structure OK (install PyYAML for full validation)"}

    def verify_csv(self, content: str) -> dict:
        """CSV structure validation"""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        
        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return {"valid": False, "message": "✗ No rows found"}
            
            # Check consistent column count
            col_count = len(rows[0])
            for i, row in enumerate(rows[1:], 2):
                if len(row) != col_count:
                    return {"valid": False, "message": f"✗ Row {i}: Expected {col_count} columns, got {len(row)}"}
            
            return {"valid": True, "message": f"✓ Valid CSV: {len(rows)} rows, {col_count} columns"}
        except csv.Error as e:
            return {"valid": False, "message": f"✗ CSV Error: {str(e)}"}

    def verify_document_basic(self, content: str, file_type: str) -> dict:
        """Basic checks for document formats (.doc, .pdf, .epub) — text extraction layer"""
        if not content.strip():
            return {"valid": False, "message": f"✗ Empty {file_type} content"}
        
        # For binary formats, we verify the extracted/plaintext content
        # Actual binary validation would require libraries like python-docx, PyPDF2, etc.
        
        # Basic structure checks
        if len(content) < 50:
            return {"valid": False, "message": f"✗ {file_type} content too short"}
        
        # Check for reasonable paragraph structure
        if len(content) > 500 and '\n\n' not in content and '\n' not in content:
            return {"valid": False, "message": f"✗ {file_type} lacks paragraph breaks"}
        
        return {"valid": True, "message": f"✓ {file_type.upper()} content structure OK"}

    def verify_file(self, filename: str, content: str) -> dict:
        """Routes to the correct verifier based on extension"""
        ext = Path(filename).suffix.lower()
        
        verifiers = {
            '.py': self.verify_python,
            '.json': self.verify_json,
            '.txt': self.verify_text_quality,
            '.md': self.verify_text_quality,
            '.js': self.verify_javascript,
            '.jsx': self.verify_javascript,
            '.ts': self.verify_javascript,
            '.tsx': self.verify_javascript,
            '.yaml': self.verify_yaml,
            '.yml': self.verify_yaml,
            '.csv': self.verify_csv,
            # Document formats — verify extracted text content
            '.doc': lambda c: self.verify_document_basic(c, 'doc'),
            '.docx': lambda c: self.verify_document_basic(c, 'docx'),
            '.pdf': lambda c: self.verify_document_basic(c, 'pdf'),
            '.epub': lambda c: self.verify_document_basic(c, 'epub'),
            # Add more as needed
        }
        
        verifier = verifiers.get(ext)
        if verifier:
            return verifier(content)
        
        # Fallback for unknown types
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        return {"valid": True, "message": "✓ Basic check passed"}
