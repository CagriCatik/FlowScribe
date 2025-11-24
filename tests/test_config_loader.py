import os
from pathlib import Path

from flowscribe.config.loader import load_config, apply_cli_overrides
from flowscribe.config.model import AppConfig


def test_load_default(tmp_path: Path, monkeypatch):
    cfg = load_config(tmp_path / "missing.toml")
    assert isinstance(cfg, AppConfig)


def test_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FS_LLM_HOST", "http://envhost")
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.llm.host == "http://envhost"


def test_cli_override(tmp_path: Path):
    base = load_config(tmp_path / "missing.toml")
    merged = apply_cli_overrides(base, {"input_path": str(tmp_path), "output_dir": str(tmp_path / "out"), "model": "m1"})
    assert merged.paths.input_path == tmp_path
    assert merged.llm.model == "m1"
    assert merged.paths.output_dir == tmp_path / "out"
