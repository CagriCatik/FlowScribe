from pathlib import Path
import pytest
from flowscribe.core.json_io import load_workflow, JSONLoadError


def test_load_workflow(tmp_path: Path):
    path = tmp_path / "flow.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    wf = load_workflow(path)
    assert wf.path == path
    assert "\n" in wf.pretty


def test_invalid_json(tmp_path: Path):
    path = tmp_path / "invalid.json"
    path.write_text('{"a": }', encoding="utf-8")
    with pytest.raises(JSONLoadError):
        load_workflow(path)
