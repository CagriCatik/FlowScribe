"""Output writers for FlowScribe."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..logging import get_logger

logger = get_logger(__name__)


class OutputWriteError(Exception):
    """Raised when documentation cannot be written to disk."""


@dataclass(slots=True)
class MarkdownDocument:
    path: Path
    content: str


def compute_output_path(output_root: Path, base_input: Path, workflow_path: Path) -> Path:
    try:
        rel = workflow_path.relative_to(base_input)
        rel_dir = rel.parent
    except ValueError:
        rel_dir = Path(".")
    return output_root / rel_dir / f"{workflow_path.stem}.md"


def write_markdown(output_root: Path, base_input: Path, workflow_path: Path, content: str) -> MarkdownDocument:
    out_path = compute_output_path(output_root, base_input, workflow_path)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
    except Exception as exc:
        raise OutputWriteError(f"Failed to write markdown to {out_path}: {exc}") from exc
    logger.info("Markdown description exported: %s", out_path)
    return MarkdownDocument(path=out_path, content=content)
