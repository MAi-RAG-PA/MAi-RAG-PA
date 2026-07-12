# app/agents/verifier.py
import ast
import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


class ContentVerifier:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def verify_python(self, content: str) -> Dict[str, Any]:
        """Verify that Python content parses without a SyntaxError."""
        try:
            ast.parse(content)
            return {"valid": True, "message": "✓ Syntax OK"}
        except SyntaxError as e:
            return {"valid": False, "message": f"✗ SyntaxError: {e}"}

    def verify_json(self, content: str) -> Dict[str, Any]:
        """Verify that content is valid JSON."""
        try:
            json.loads(content)
            return {"valid": True, "message": "✓ Valid JSON"}
        except json.JSONDecodeError as e:
            return {"valid": False, "message": f"✗ JSONError: {e}"}

    def verify_text_quality(self, content: str) -> Dict[str, Any]:
        """Heuristic checks for plain text/markdown structure and basic quality."""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}

        if len(content) > 500 and "\n\n" not in content:
            return {
                "valid": False,
                "message": "✗ Long text lacks paragraph breaks",
            }

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if lines:
            first = lines[0]
            if not first[0].isupper() and not first.startswith(("-", "*", "#")):
                return {
                    "valid": False,
                    "message": "✗ First line should start with capital or marker",
                }

        if re.search(r"(.)\1{4,}", content):
            return {
                "valid": False,
                "message": "✗ Excessive character repetition",
            }

        typos = {"teh": "the", "adn": "and", "recieve": "receive"}
        for typo, correct in typos.items():
            if re.search(rf"\b{typo}\b", content, re.IGNORECASE):
                return {
                    "valid": False,
                    "message": f"✗ Possible typo: '{typo}' → '{correct}'",
                }

        return {"valid": True, "message": "✓ Text structure OK"}

    def verify_javascript(self, content: str) -> Dict[str, Any]:
        """Basic JavaScript structure checks (no external parser)."""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}

        stack = []
        pairs = {"{": "}", "[": "]", "(": ")"}
        closing = set(pairs.values())

        for char in content:
            if char in pairs:
                stack.append(char)
            elif char in closing:
                if not stack or pairs[stack.pop()] != char:
                    return {
                        "valid": False,
                        "message": f"✗ Unbalanced bracket: {char}",
                    }

        if stack:
            return {
                "valid": False,
                "message": f"✗ Unclosed bracket: {stack[-1]}",
            }

        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("//")
        ]
        for line in lines:
            if re.match(r"^(function|const|let|var|class)\s+\w+\s*[=(\{]?", line):
                if not line.rstrip().endswith(("{", ";", ")", "}")) and "=" not in line:
                    return {
                        "valid": False,
                        "message": "✗ Possible missing semicolon or block",
                    }

        return {"valid": True, "message": "✓ JavaScript structure OK"}

    def verify_yaml(self, content: str) -> Dict[str, Any]:
        """YAML structure validation using safe load."""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}

        try:
            import yaml

            yaml.safe_load(content)
            return {"valid": True, "message": "✓ Valid YAML structure"}
        except ImportError:
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if not line.strip() or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip())
                if indent % 2 != 0 and indent > 0:
                    return {
                        "valid": False,
                        "message": f"✗ Line {i}: Inconsistent indentation",
                    }
            return {
                "valid": True,
                "message": "✓ Basic YAML structure OK (install PyYAML for full validation)",
            }
        except Exception as e:
            return {"valid": False, "message": f"✗ YAML Error: {str(e)}"}

    def verify_csv(self, content: str) -> Dict[str, Any]:
        """CSV structure validation."""
        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}

        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return {"valid": False, "message": "✗ No rows found"}

            col_count = len(rows[0])
            for i, row in enumerate(rows[1:], 2):
                if len(row) != col_count:
                    return {
                        "valid": False,
                        "message": (
                            f"✗ Row {i}: Expected {col_count} columns, "
                            f"got {len(row)}"
                        ),
                    }

            return {
                "valid": True,
                "message": f"✓ Valid CSV: {len(rows)} rows, {col_count} columns",
            }
        except csv.Error as e:
            return {"valid": False, "message": f"✗ CSV Error: {str(e)}"}

    def verify_document_basic(
        self,
        content: str,
        file_type: str,
    ) -> Dict[str, Any]:
        """Basic checks for document formats (.doc, .pdf, .epub) — text extraction layer."""
        if not content.strip():
            return {
                "valid": False,
                "message": f"✗ Empty {file_type} content",
            }

        if len(content) < 50:
            return {
                "valid": False,
                "message": f"✗ {file_type} content too short",
            }

        if len(content) > 500 and "\n\n" not in content and "\n" not in content:
            return {
                "valid": False,
                "message": f"✗ {file_type} lacks paragraph breaks",
            }

        return {
            "valid": True,
            "message": f"✓ {file_type.upper()} content structure OK",
        }

    def verify_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Route to the correct verifier based on file extension."""
        suffixes = Path(filename).suffixes
        ext = "".join(suffixes).lower() if suffixes else ""

        verifiers = {
            ".py": self.verify_python,
            ".json": self.verify_json,
            ".txt": self.verify_text_quality,
            ".md": self.verify_text_quality,
            ".js": self.verify_javascript,
            ".jsx": self.verify_javascript,
            ".ts": self.verify_javascript,
            ".tsx": self.verify_javascript,
            ".yaml": self.verify_yaml,
            ".yml": self.verify_yaml,
            ".csv": self.verify_csv,
            ".doc": lambda c: self.verify_document_basic(c, "doc"),
            ".docx": lambda c: self.verify_document_basic(c, "docx"),
            ".pdf": lambda c: self.verify_document_basic(c, "pdf"),
            ".epub": lambda c: self.verify_document_basic(c, "epub"),
        }

        verifier = verifiers.get(ext) or verifiers.get(Path(filename).suffix.lower())
        if verifier:
            return verifier(content)

        if not content.strip():
            return {"valid": False, "message": "✗ Empty content"}
        return {"valid": True, "message": "✓ Basic check passed"}


def verify_content(
    filename: str,
    content: str,
    workspace: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Standalone function to verify file content.

    Args:
        filename: Name of the file (used to determine verification method)
        content: The file content to verify
        workspace: Optional workspace path

    Returns:
        dict with 'valid' (bool) and 'message' (str) keys.
    """
    if workspace is None:
        workspace = Path.home() / "MAi-RAG-PA" / "workspace"

    verifier = ContentVerifier(workspace)
    return verifier.verify_file(filename, content)
