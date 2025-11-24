"""Workflow discovery utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from ..logging import get_logger

logger = get_logger(__name__)


class DiscoveryError(Exception):
    """Raised when discovery cannot proceed."""


def is_json_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".json"


def discover_workflows(input_path: Path) -> List[Path]:
    """Discover JSON workflow files from the provided path."""

    if input_path.is_file() and is_json_file(input_path):
        return [input_path]
    if input_path.is_dir():
        files = sorted([p for p in input_path.rglob("*.json") if p.is_file()])
        return files
    raise DiscoveryError(f"Input path is neither a file nor directory: {input_path}")


def filter_selection(all_paths: Iterable[Path], selected: Iterable[Path] | None) -> List[Path]:
    if selected is None:
        return list(all_paths)
    selected_set = {p.resolve() for p in selected}
    return [p for p in all_paths if p.resolve() in selected_set]
