"""
Diagnostics Normalization Layer

Unified issue schema for all parser/compiler/linter outputs.
Every analysis backend normalizes its output to NormalizedIssue.
This is the single source of truth for issue data flowing through the system.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

IssueSeverity = Literal["error", "warning", "info", "security", "bug"]
IssueCategory = Literal["syntax", "semantic", "type", "runtime-risk", "quality", "security", "style"]
IssueOrigin = Literal["parser", "compiler", "linter", "heuristic", "llm"]


@dataclass
class NormalizedIssue:
    """Single unified issue from any parser/compiler/linter backend."""

    # Identity
    id: str
    language: str

    # Classification
    severity: IssueSeverity
    category: IssueCategory

    # Message
    message: str
    explanation: str = ""

    # Location
    line: int = 0
    column: int = 0
    end_line: int = 0
    end_column: int = 0

    # Source context
    source_line: str = ""
    code_frame: str = ""

    # Fix guidance
    fix_hint: str = ""

    # Trust / provenance
    confidence: float = 1.0
    origin: IssueOrigin = "parser"
    parser_name: str = ""
    backend_name: str = ""

    # Raw data preserved for debugging only — not serialized to API
    raw_diagnostic: Optional[Any] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Serialize to dict for API responses (backward-compatible shape)."""
        return {
            "id": self.id,
            "language": self.language,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "explanation": self.explanation,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "source_line": self.source_line,
            "code_frame": self.code_frame,
            "fix_hint": self.fix_hint,
            "confidence": self.confidence,
            "origin": self.origin,
            "parser_name": self.parser_name,
            "backend_name": self.backend_name,
        }


@dataclass
class ParseResult:
    """Result from a language parser/compiler run."""

    language: str
    parser_name: str
    backend_name: str
    issues: list
    parse_success: bool      # True if parser ran without crashing
    is_fallback: bool        # True if this used a fallback/heuristic path
    fallback_reason: str = ""
    parser_confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    @property
    def has_syntax_errors(self) -> bool:
        return any(i.category == "syntax" and i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    def to_legacy_issues(self) -> list[dict]:
        """Convert to the legacy dict list format for backward compatibility."""
        return [i.to_dict() for i in self.issues]


def make_issue_id(language: str, category: str, line: int, message: str) -> str:
    """Generate a stable, short ID for an issue."""
    key = f"{language}:{category}:{line}:{message[:40]}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def build_code_frame(source_lines: list[str], line: int, column: int = 0, context: int = 2) -> str:
    """Build a code frame string showing the issue location in context."""
    if not source_lines or line <= 0:
        return ""
    idx = line - 1
    start = max(0, idx - context)
    end = min(len(source_lines), idx + context + 1)
    frame_lines = []
    for i in range(start, end):
        prefix = ">" if i == idx else " "
        frame_lines.append(f"  {prefix} {i+1:4d} | {source_lines[i]}")
        if i == idx and column > 0:
            frame_lines.append(" " * (column + 9) + "^")
    return "\n".join(frame_lines)
