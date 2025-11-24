from pathlib import Path
from flowscribe.core.discovery import discover_workflows, DiscoveryError


def test_discover_single_file(tmp_path: Path):
    json_file = tmp_path / "test.json"
    json_file.write_text("{}", encoding="utf-8")
    files = discover_workflows(json_file)
    assert files == [json_file]


def test_discover_directory(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    f1 = tmp_path / "a.json"
    f2 = sub / "b.json"
    f1.write_text("{}", encoding="utf-8")
    f2.write_text("{}", encoding="utf-8")
    files = discover_workflows(tmp_path)
    assert files == [f1, f2]


def test_discover_invalid(tmp_path: Path):
    with open(tmp_path / "notjson.txt", "w", encoding="utf-8") as f:
        f.write("hi")
    try:
        discover_workflows(tmp_path / "missing")
    except DiscoveryError:
        return
    assert False, "Expected DiscoveryError"
