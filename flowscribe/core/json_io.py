"""JSON loading and representation for workflows."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from ..logging import get_logger

logger = get_logger(__name__)


class JSONLoadError(Exception):
    """Raised when a workflow JSON file cannot be loaded."""


@dataclass(slots=True)
class WorkflowDocument:
    path: Path
    raw: Dict[str, Any]
    pretty: str

    @property
    def filename(self) -> str:
        return self.path.name


def load_workflow(path: Path) -> WorkflowDocument:
    try:
        with path.open("r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
    except Exception as exc:
        raise JSONLoadError(f"Failed to parse JSON at {path}: {exc}") from exc

    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    logger.debug("Loaded workflow %s (length=%d)", path, len(pretty))
    return WorkflowDocument(path=path, raw=data, pretty=pretty)
